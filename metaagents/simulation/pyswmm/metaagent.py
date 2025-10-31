"""
PySWMM Metaagent for XMPro DataStreams (v4 - Simplified Output)
Jaun van Heerden, 2025

A metaagent for running SWMM simulations with dynamic modifications.
Supports multiple source types: local, S3, GitHub, HTTP.
Uploads simulation results AND simulation files (.out, _mod.inp, .rpt) to S3.
Returns only the S3 path to the .rpt file for simplified downstream processing.

Changelog:
    v0.5 - 2025/10/29 - Simplified output to only return .rpt S3 path
    v0.4 - 2025/10/29 - Added upload of .out, _mod.inp, and .rpt files to S3
    v0.3 - 2025/10/24 - Made S3 settings and other configurations configurable
    v0.2 - 2025/10/17 - Refactored for better pythonic style
    v0.1 - 2025/10/16 - Initial version
"""

#TODO - Multiple scenarios
#TODO - Full PySWMM modification capabilities
#TODO - hotstart option
#TODO - progress callback


from __future__ import annotations

# --- dataclass runtime guard (fixes NoneType __dict__ crash) ---
import sys, types
if not isinstance(__name__, str) or __name__ not in sys.modules:
    module_name = "xmtwin_runtime"  # any stable name is fine
    globals()["__name__"] = module_name
    mod = types.ModuleType(module_name)
    mod.__dict__.update(globals())
    sys.modules[module_name] = mod
# --- end guard ---

import gc
import gzip
import json
import logging
import os
import shutil
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Protocol
from urllib.parse import urlparse

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):  # polyfill
        pass

from pyswmm import Simulation, SimulationPreConfig, Output
from swmm.toolkit.shared_enum import (
    SubcatchAttribute as SA,
    NodeAttribute as NA,
    LinkAttribute as LA,
    SystemAttribute as SYSA,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# --- Constants ---
class SourceType(StrEnum):
    """Supported network file source types."""
    LOCAL = "local"
    S3 = "s3"
    GITHUB = "github"
    HTTP = "http"


class SWMMSection(StrEnum):
    """SWMM input file sections that can be modified."""
    OPTIONS = "OPTIONS"
    TIMESERIES = "TIMESERIES"


# S3 upload settings
S3_JSON_EXTRA_ARGS = {
    "ContentType": "application/json",
    "ContentEncoding": "gzip",
    "CacheControl": "public, max-age=31536000, immutable"
}

S3_MANIFEST_EXTRA_ARGS = {
    "ContentType": "application/json",
    "CacheControl": "public, max-age=300"
}

# S3 upload settings for simulation files
S3_OUT_FILE_EXTRA_ARGS = {
    "ContentType": "application/octet-stream",
    "CacheControl": "public, max-age=31536000, immutable"
}

S3_INP_FILE_EXTRA_ARGS = {
    "ContentType": "text/plain",
    "CacheControl": "public, max-age=31536000, immutable"
}

S3_RPT_FILE_EXTRA_ARGS = {
    "ContentType": "text/plain",
    "CacheControl": "public, max-age=31536000, immutable"
}

# Attributes to export for each entity type
SYSTEM_ATTRS = [SYSA.RAINFALL, SYSA.RUNOFF_FLOW, SYSA.OUTFALL_FLOWS, SYSA.SNOW_DEPTH]
SUBCATCH_ATTRS = [SA.RAINFALL, SA.RUNOFF_RATE, SA.SNOW_DEPTH, SA.EVAP_LOSS, SA.INFIL_LOSS, SA.SOIL_MOISTURE]
NODE_ATTRS = [NA.INVERT_DEPTH, NA.HYDRAULIC_HEAD, NA.TOTAL_INFLOW, NA.LATERAL_INFLOW, NA.FLOODING_LOSSES]
LINK_ATTRS = [LA.FLOW_RATE, LA.FLOW_DEPTH, LA.FLOW_VELOCITY, LA.FLOW_VOLUME]


# --- Data Classes ---
@dataclass
class NetworkConfig:
    """Configuration for SWMM network file."""
    network_file: str
    source_type: SourceType
    network_file_local: str | None = None
    temp_dir: str | None = None

    def __post_init__(self):
        """Validate and convert source_type to enum."""
        if isinstance(self.source_type, str):
            self.source_type = SourceType(self.source_type.lower())


@dataclass
class S3Config:
    """Configuration for S3 upload settings."""
    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str = "us-east-1"
    bucket: str = "xmtwin"
    prefix_base: str = "water_utilities/flood_management"


@dataclass
class SimulationState:
    """Global state management for the metaagent."""
    config: NetworkConfig | None = None
    s3_config: S3Config | None = None
    s3_client: Any = None  # boto3 client

    def reset(self) -> None:
        """Reset state to initial condition."""
        self.config = None
        self.s3_config = None
        self.s3_client = None


# Global state instance
_state = SimulationState()


# --- File Download Protocols ---
class FileDownloader(Protocol):
    """Protocol for file download implementations."""

    def download(self, source: str, dest_dir: str) -> str:
        """Download file from source to destination directory."""
        ...


class S3Downloader:
    """Download files from AWS S3."""

    def download(self, s3_path: str, dest_dir: str) -> str:
        """Download file from S3 to local directory."""
        import boto3
        from botocore.exceptions import ClientError

        # Parse s3://bucket/key
        parts = s3_path[5:].split('/', 1)
        bucket, key = parts[0], parts[1]
        filename = Path(key).name
        dest_path = Path(dest_dir) / filename

        try:
            s3_client = boto3.client('s3')
            logger.info(f"Downloading s3://{bucket}/{key} to {dest_path}")
            s3_client.download_file(bucket, key, str(dest_path))
            return str(dest_path)
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            print(e)


class HTTPDownloader:
    """Download files from HTTP/HTTPS URLs (including GitHub)."""

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL, converting GitHub URLs to raw content URLs."""
        if 'github.com' in url and 'raw.githubusercontent.com' not in url:
            return url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        return url

    def download(self, url: str, dest_dir: str) -> str:
        """Download file from HTTP/HTTPS URL."""
        import requests

        url = self._normalize_url(url)
        filename = Path(urlparse(url).path).name or 'downloaded_file.inp'
        dest_path = Path(dest_dir) / filename

        logger.info(f"Downloading {url} to {dest_path}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            dest_path.write_bytes(response.content)
            return str(dest_path)
        except requests.RequestException as e:
            logger.error(f"Failed to download from {url}: {e}")
            print(e)


class FileSourceManager:
    """Manage file downloads from various sources."""

    _http_downloader = HTTPDownloader()
    _downloaders = {
        SourceType.S3: S3Downloader(),
        SourceType.GITHUB: _http_downloader,
        SourceType.HTTP: _http_downloader,
    }

    @classmethod
    def get_local_path(
        cls,
        network_file: str,
        source_type: SourceType,
        temp_dir: str | None = None
    ) -> str:
        """
        Get local file path, downloading if necessary.

        Args:
            network_file: Path or URL to network file
            source_type: Source type enum
            temp_dir: Optional temp directory for downloads

        Returns:
            Local file path

        Raises:
            FileNotFoundError: If local file doesn't exist
            RuntimeError: If download fails
        """
        if source_type == SourceType.LOCAL:
            return str(Path(network_file).resolve())

        # Create temp directory if needed and download file
        download_dir = temp_dir or mkdtemp(prefix='swmm_')
        downloader = cls._downloaders.get(source_type)
        return downloader.download(network_file, download_dir)


# --- Helper Functions ---

def _now_run_id() -> str:
    """Generate a run ID based on current timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(":", "").replace("+00:00", "Z")


def _format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string with Z suffix."""
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def upload_grouped_json_to_s3(run_id: str, local_dir: Path, s3_client: Any, bucket: str, base_prefix: str) -> dict[str, Any]:
    """
    Upload grouped JSON files to S3.

    Args:
        run_id: Unique run identifier
        local_dir: Local directory containing JSON files
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        base_prefix: Base S3 prefix path

    Returns:
        Dict with upload summary
    """
    prefix = f"{base_prefix}/{run_id}"
    file_names = ["system.json.gz", "subcatchments.json.gz", "nodes.json.gz", "links.json.gz"]
    artifacts = []

    for name in file_names:
        fp = local_dir / name
        if fp.exists():
            key = f"{prefix}/{name}"
            s3_client.upload_file(str(fp), bucket, key, ExtraArgs=S3_JSON_EXTRA_ARGS)
            artifacts.append({"key": key})

    # Create and upload manifest
    manifest = {
        "run_id": run_id,
        "groups": ["system", "subcatchments", "nodes", "links"],
        "files": {name.replace(".json.gz", ""): name for name in file_names}
    }
    man = local_dir / "manifest.json"
    man.write_text(json.dumps(manifest, ensure_ascii=False))
    s3_client.upload_file(str(man), bucket, f"{prefix}/manifest.json", ExtraArgs=S3_MANIFEST_EXTRA_ARGS)

    return {"bucket": bucket, "prefix": prefix, "objects": artifacts + [{"key": f"{prefix}/manifest.json"}]}


def upload_simulation_files_to_s3(
    run_id: str,
    network_file_local: str,
    s3_client: Any,
    bucket: str,
    base_prefix: str
) -> dict[str, Any]:
    """
    Upload simulation files (.out, _mod.inp, .rpt) to S3 with standardized names.

    Args:
        run_id: Unique run identifier
        network_file_local: Local path to the network file
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        base_prefix: Base S3 prefix path

    Returns:
        Dict with upload summary
    """
    prefix = f"{base_prefix}/{run_id}"
    base_path = network_file_local.replace(".inp", "")
    uploaded_files = []

    # Define file specs: (local_path, s3_filename, extra_args)
    file_specs = [
        (f"{base_path}_mod.out", "network_mod.out", S3_OUT_FILE_EXTRA_ARGS),
        (f"{base_path}_mod.inp", "network_mod.inp", S3_INP_FILE_EXTRA_ARGS),
        (f"{base_path}_mod.rpt", "network_mod.rpt", S3_RPT_FILE_EXTRA_ARGS),
    ]

    for local_path_str, s3_filename, extra_args in file_specs:
        local_path = Path(local_path_str)
        if local_path.exists():
            key = f"{prefix}/{s3_filename}"
            try:
                s3_client.upload_file(str(local_path), bucket, key, ExtraArgs=extra_args)
                uploaded_files.append({"key": key, "file": s3_filename})
                logger.info(f"Uploaded {s3_filename} to S3: {key}")
            except Exception as e:
                logger.warning(f"Failed to upload {s3_filename}: {e}")
        else:
            logger.warning(f"Simulation file not found: {local_path}")

    return {
        "bucket": bucket,
        "prefix": prefix,
        "simulation_files": uploaded_files
    }


# --- JSON Export Functions ---
def _json_array_writer_gz(path: Path):
    """Write a JSON object like {"meta": {...}, "series": {...}} with streaming arrays per id.
       Returns small helpers to open per-id arrays, append rows, and close cleanly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    f = gzip.open(path, "wt", encoding="utf-8")
    f.write('{"meta":{')
    # You can write meta later via direct f.write if desired; keep it simple for now.
    f.write('},"series":{')
    first_id = True

    def open_id(id_):
        nonlocal first_id
        if not first_id: f.write(",")
        first_id = False
        f.write(json.dumps(id_)); f.write(":{")  # start object for this id
        return _PerIdWriter(f)

    def close():
        f.write("}}")
        f.close()

    class _PerIdWriter:
        def __init__(self, fileobj):
            self.f = fileobj
            self._first_attr = True
            self._open_arrays = set()

        def open_attr(self, attr_name):
            if not self._first_attr: self.f.write(",")
            self._first_attr = False
            self.f.write(json.dumps(attr_name)); self.f.write(":[")  # start array
            self._open_arrays.add(attr_name)
            return _AttrAppender(self.f, self._open_arrays, attr_name)

        def close_id(self):
            # close any arrays not explicitly closed (safety)
            # (In our use we always close per-attr properly.)
            self.f.write("}")

    class _AttrAppender:
        def __init__(self, fileobj, registry, attr_name):
            self.f = fileobj
            self._first = True
            self._registry = registry
            self._attr = attr_name
        def append(self, ts_iso, value):
            if not self._first: self.f.write(",")
            self._first = False
            # [timestamp, value]
            self.f.write('['); self.f.write(json.dumps(ts_iso)); self.f.write(',')
            # keep float compact
            self.f.write(json.dumps(float(value))); self.f.write(']')
        def close_attr(self):
            self.f.write("]")
            self._registry.discard(self._attr)

    return open_id, close

def _export_entity_json(
    fp: Path,
    entity_ids: list[str],
    attrs: list,
    series_getter,
    run_id: str
) -> Path:
    """
    Generic export function for any entity type.

    Args:
        fp: Output file path
        entity_ids: List of entity IDs to export
        attrs: List of attributes to export for each entity
        series_getter: Function to get time series data (entity_id, attr) -> series
        run_id: Run identifier

    Returns:
        Path to created file
    """
    open_id, finish = _json_array_writer_gz(fp)
    for entity_id in entity_ids:
        w = open_id(entity_id)
        for attr in attrs:
            try:
                ser = series_getter(entity_id, attr)
            except Exception:
                continue
            a = w.open_attr(attr.name)
            for ts, val in ser.items():
                a.append(_format_timestamp(ts), val)
            a.close_attr()
        w.close_id()
    finish()
    return fp


def export_system_json(out: Output, run_id: str, export_dir: Path) -> Path:
    """Export system-level attributes to JSON."""
    return _export_entity_json(
        export_dir / "system.json.gz",
        ["_"],
        SYSTEM_ATTRS,
        lambda _, attr: out.system_series(attr),
        run_id
    )


def export_subcatchments_json(out: Output, run_id: str, export_dir: Path) -> Path:
    """Export subcatchment attributes to JSON."""
    return _export_entity_json(
        export_dir / "subcatchments.json.gz",
        list(out.subcatchments),
        SUBCATCH_ATTRS,
        out.subcatch_series,
        run_id
    )


def export_nodes_json(out: Output, run_id: str, export_dir: Path) -> Path:
    """Export node attributes to JSON."""
    return _export_entity_json(
        export_dir / "nodes.json.gz",
        list(out.nodes),
        NODE_ATTRS,
        out.node_series,
        run_id
    )


def export_links_json(out: Output, run_id: str, export_dir: Path) -> Path:
    """Export link attributes to JSON."""
    return _export_entity_json(
        export_dir / "links.json.gz",
        list(out.links),
        LINK_ATTRS,
        out.link_series,
        run_id
    )




# --- PreConfig Builders ---
class PreConfigBuilder:
    """Build SimulationPreConfig with various modifications."""

    def __init__(self):
        self.preconfig = SimulationPreConfig()
        self.temp_files: dict[str, Path] = {}

    def add_options(self, options: dict[str, Any]) -> PreConfigBuilder:
        """
        Add OPTIONS section modifications.

        Args:
            options: Dict of option_name: option_value

        Returns:
            Self for chaining
        """
        for opt_name, opt_value in options.items():
            self.preconfig.add_update_by_token(
                'OPTIONS',
                opt_name.upper(),
                1,
                str(opt_value)
            )

        logger.debug(f"Added {len(options)} option modifications")
        return self

    def add_timeseries(
        self,
        timeseries_data: dict[str, list[str]],
        temp_dir: Path
    ) -> PreConfigBuilder:
        """
        Add TIMESERIES section modifications.

        Args:
            timeseries_data: Dict of timeseries_name: list of data lines
            temp_dir: Temporary directory for timeseries files

        Returns:
            Self for chaining
        """
        for ts_name, ts_lines in timeseries_data.items():
            ts_file = temp_dir / f"{ts_name}.txt"
            ts_file.write_text('\n'.join(line.rstrip() for line in ts_lines) + '\n', encoding='utf-8')
            ts_file.chmod(0o644)

            # Store reference and update preconfig
            self.temp_files[ts_name] = ts_file
            self.preconfig.add_update_by_token('TIMESERIES', ts_name, 1, 'FILE')
            self.preconfig.add_update_by_token('TIMESERIES', ts_name, 2, ts_file.resolve().as_posix())

        logger.debug(f"Added {len(timeseries_data)} timeseries modifications")
        return self

    def build(self) -> SimulationPreConfig:
        """Return the built SimulationPreConfig."""
        return self.preconfig


def _parse_input(data: Any) -> dict[str, Any]:
    """Parse input data, handling both dict and JSON string formats."""
    return json.loads(data) if isinstance(data, str) else data


def build_preconfig(
    modifications: dict[str, Any],
    temp_dir: Path
) -> SimulationPreConfig:
    """
    Build SimulationPreConfig from modification dict.

    Args:
        modifications: Dict with sections as keys (OPTIONS, TIMESERIES, etc.)
        temp_dir: Temporary directory for file-based modifications

    Returns:
        Configured SimulationPreConfig
    """
    builder = PreConfigBuilder()

    for section_name, section_data in modifications.items():
        section = section_name.upper()
        if section == SWMMSection.OPTIONS.value:
            builder.add_options(section_data)
        elif section == SWMMSection.TIMESERIES.value:
            builder.add_timeseries(section_data, temp_dir)
        else:
            logger.warning(f"Unsupported modification section: '{section_name}'")

    return builder.build()


# --- Simulation Runner ---
@contextmanager
def run_simulation(
    network_file: str,
    preconfig: SimulationPreConfig | None = None,
    progress_interval: int = 1000
):
    """
    Context manager for running SWMM simulation with proper cleanup.

    Args:
        network_file: Path to SWMM .inp file
        preconfig: Optional SimulationPreConfig for modifications
        progress_interval: Print progress every N steps

    Yields:
        Simulation object
    """
    sim = None
    try:
        sim = Simulation(network_file, sim_preconfig=preconfig)
        logger.info(f"Starting simulation: {network_file}")

        with sim:
            for step_idx, step in enumerate(sim):
                if step_idx % progress_interval == 0:
                    logger.debug(f"Step {step_idx}: {step}")

        logger.info("Simulation completed successfully")
        yield sim

    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise

    finally:
        if sim is not None:
            # Cleanup simulation resources
            if hasattr(sim, 'close'):
                try:
                    sim.close()
                except Exception as e:
                    logger.warning(f"Error closing simulation: {e}")
            del sim

        gc.collect()

        # Windows needs extra time for file handle cleanup
        if os.name == 'nt':
            time.sleep(0.5)


# --- Metaagent Interface Functions ---
def on_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Initialize the metaagent with network and S3 configuration.

    Expected data format:
    {
        "network_file": "path/to/file.inp",  # or s3://bucket/key or URL
        "source_type": "local",  # or "s3", "github", "http"
        "temp_dir": "/optional/temp/dir",  # optional
        # S3 settings (optional - required only if uploading to S3)
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY",
        "region_name": "us-east-1",
        "bucket": "xmtwin",
        "prefix_base": "water_utilities/flood_management"
    }

    Args:
        data: Configuration dictionary

    Returns:
        Status dictionary with initialization results

    Raises:
        ValueError: If network_file missing or source_type invalid
        RuntimeError: If file download/access fails
    """
    global _state

    # Extract configuration parameters
    network_file = data.get('network_file')
    source_type_str = data.get('source_type', 'local')
    temp_dir = data.get('temp_dir')

    # Create network configuration
    config = NetworkConfig(
        network_file=network_file,
        source_type=source_type_str,
        temp_dir=temp_dir
    )

    # Get local file path (downloads if necessary)
    local_path = FileSourceManager.get_local_path(
        config.network_file,
        config.source_type,
        config.temp_dir
    )
    config.network_file_local = local_path

    # Store network config in global state
    _state.config = config

    # Configure S3 settings if provided (check for any S3 keys)
    aws_access_key_id = data.get('aws_access_key_id')
    if aws_access_key_id:
        import boto3

        # Create S3Config with flattened parameters
        s3_config = S3Config(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=data.get('aws_secret_access_key', ''),
            region_name=data.get('region_name', 'us-east-1'),
            bucket=data.get('bucket', 'xmtwin'),
            prefix_base=data.get('prefix_base', 'water_utilities/flood_management')
        )

        # Create S3 client with provided credentials
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=s3_config.aws_access_key_id,
            aws_secret_access_key=s3_config.aws_secret_access_key,
            region_name=s3_config.region_name
        )

        _state.s3_config = s3_config
        _state.s3_client = s3_client
        logger.info(f"S3 configured: bucket={s3_config.bucket}, region={s3_config.region_name}")

    logger.info(f"Metaagent initialized: {config.source_type.value} source")

    return {
        'status': 'initialized',
        'network_file_original': network_file,
        'network_file_local': local_path,
        'source_type': config.source_type.value,
        's3_configured': aws_access_key_id is not None
    }


def on_receive(data: dict[str, Any]) -> dict[str, Any]:
    """
    Run simulation with optional modifications and return S3 path to .rpt file.

    Expected data format:
    {
        "modifications": {
            "options": {
                "start_date": "10/22/2025",
                "end_date": "10/22/2025"
            },
            "timeseries": {
                "rain1": ["10/22/2025  00:00:00  0.00", ...]
            }
        }
    }

    Args:
        data: Data dictionary with optional modifications

    Returns:
        Simplified results dictionary with only status, run_id, and rpt_s3_path

    Raises:
        RuntimeError: If metaagent not initialized or simulation fails
    """
    global _state

    modifications = data.get('modifications', {})
    modifications_parsed = _parse_input(modifications)

    # Use temporary directory for timeseries files
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Build preconfig if modifications provided
        preconfig = None
        if modifications_parsed:
            preconfig = build_preconfig(modifications_parsed, temp_path)
            logger.info(f"Built preconfig with {len(modifications_parsed)} section(s)")

        # Run simulation
        with run_simulation(_state.config.network_file_local, preconfig):
            pass  # Simulation runs in context manager

        # Export grouped JSON (gz) to /exports
        export_dir = temp_path / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        run_id = _now_run_id()

        with Output(f'{_state.config.network_file_local.replace(".inp", "_mod.out")}') as out:
            export_links_json(out, run_id, export_dir)
            export_nodes_json(out, run_id, export_dir)
            export_subcatchments_json(out, run_id, export_dir)
            export_system_json(out, run_id, export_dir)

        # Upload to S3 if configured
        if _state.s3_client and _state.s3_config:
            # Upload JSON results
            upload_grouped_json_to_s3(
                run_id=run_id,
                local_dir=export_dir,
                s3_client=_state.s3_client,
                bucket=_state.s3_config.bucket,
                base_prefix=_state.s3_config.prefix_base
            )

            # Upload simulation files (.out, _mod.inp, .rpt)
            upload_simulation_files_to_s3(
                run_id=run_id,
                network_file_local=_state.config.network_file_local,
                s3_client=_state.s3_client,
                bucket=_state.s3_config.bucket,
                base_prefix=_state.s3_config.prefix_base
            )

            # Construct the S3 path to the .rpt file
            rpt_s3_path = f"s3://{_state.s3_config.bucket}/{_state.s3_config.prefix_base}/{run_id}/network_mod.rpt"

            logger.info(f"Simulation completed. RPT file available at: {rpt_s3_path}")

            return {
                'status': 'completed',
                'run_id': run_id,
                'rpt_s3_path': rpt_s3_path
            }
        else:
            logger.warning("S3 not configured, results not uploaded")
            return {
                'status': 'completed',
                'run_id': run_id,
                'rpt_s3_path': None
            }


def on_destroy(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Clean up metaagent resources.

    Args:
        data: Optional data dictionary (unused)

    Returns:
        Status dictionary
    """
    global _state

    if _state.config is None:
        return {'status': 'already_destroyed'}

    # Clean up downloaded files if not local
    if _state.config.source_type != SourceType.LOCAL:
        local_path = _state.config.network_file_local
        if local_path:
            temp_dir = Path(local_path).parent

            # Only delete if it's a temp directory
            if 'swmm_' in str(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    # Reset state
    _state.reset()
    logger.info("Metaagent destroyed")

    return {'status': 'destroyed'}
