"""
src/services/app_state.py

Centralized Streamlit session state manager.

Dataset identity contract
─────────────────────────
Every time a pipeline run completes successfully the following keys are stored
in st.session_state:

  ACTIVE_DATASET     – basename of the active CSV (or data mode string)
  ACTIVE_DATASET_SIG – MD5 signature of the file (size + mtime based)
  raw_df             – the raw DataFrame as fetched from the provider
  processed_df       – the pre-processed DataFrame
  pipeline_results   – the final scored / planned / communicated DataFrame
  fairness_warnings  – list of FairnessWarning objects
  baseline_results   – BaselineRunResult from dataset_id         – governance registry ID
  dataset_rows       – row count (visible to UI)
  pipeline_duration_s – wall-clock duration
  provider_metadata  – raw dict from the provider

When the user switches dataset/mode ALL of the above are cleared so stale
data can never bleed into a new run.
"""
import streamlit as st
from src.config.settings import settings
from src.services.pipeline_service import PipelineService

# Keys that carry derived data and must be cleared on dataset change.
_PIPELINE_STATE_KEYS = [
    "pipeline_results",
    "raw_df",
    "processed_df",
    "fairness_warnings",
    "baseline_results",
    "dataset_id",
    "dataset_rows",
    "dataset_signature",
    "dataset_name",
    "pipeline_duration_s",
    "provider_metadata",
    "app_status",
    "app_errors",
    "ACTIVE_DATASET",
    "ACTIVE_DATASET_SIG",
]


class AppState:
    """Manages the Streamlit session state and application initialization."""

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _current_dataset_key() -> str:
        """Return a string that uniquely identifies the currently selected dataset."""
        mode = settings.data_mode.upper()
        if mode == "CSV_DATA":
            return settings.active_csv_dataset
        return mode  # e.g. "SYNTHETIC", "HYBRID"

    @staticmethod
    def _current_dataset_signature() -> str:
        """Return the file-level signature (or empty string for non-CSV modes)."""
        mode = settings.data_mode.upper()
        if mode != "CSV_DATA":
            return ""
        import os
        from src.data_providers.csv_provider import get_dataset_signature
        file_path = os.path.join(settings.raw_data_dir, settings.active_csv_dataset)
        return get_dataset_signature(file_path).get("signature", "")

    @staticmethod
    def _dataset_changed() -> bool:
        """
        Return True if the currently configured dataset differs from what is
        cached in session state (i.e. the user has switched datasets/mode).
        """
        cached_key = st.session_state.get("ACTIVE_DATASET", "")
        cached_sig = st.session_state.get("ACTIVE_DATASET_SIG", "")
        current_key = AppState._current_dataset_key()
        current_sig = AppState._current_dataset_signature()
        return cached_key != current_key or (current_sig and cached_sig != current_sig)

    @staticmethod
    def _clear_all_pipeline_state() -> None:
        """Remove every derived pipeline key from session state."""
        for key in _PIPELINE_STATE_KEYS:
            st.session_state.pop(key, None)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def initialize_application(force_refresh: bool = False) -> None:
        """
        Initializes (or re-initializes) the application pipeline.

        Triggers a re-run when:
          • pipeline_results has never been set  (first boot)
          • force_refresh=True                   (manual refresh button)
          • the active dataset/mode has changed  (dataset switch)
          • the active CSV file has been modified (file-level cache invalidation)
        """
        needs_run = (
            force_refresh
            or "pipeline_results" not in st.session_state
            or AppState._dataset_changed()
        )

        if not needs_run:
            return

        # Clear ALL stale state before running a fresh pipeline
        AppState._clear_all_pipeline_state()

        with st.spinner("🔄 Running pipeline — loading dataset and computing risk scores…"):
            results = PipelineService.run_full_pipeline()

        st.session_state.app_status = results["status"]
        st.session_state.app_errors = results.get("errors", [])

        if results["status"] == "SUCCESS":
            st.session_state.raw_df              = results["raw_df"]
            st.session_state.processed_df        = results["processed_df"]
            st.session_state.pipeline_results    = results["pipeline_results"]
            st.session_state.fairness_warnings   = results["fairness_warnings"]
            st.session_state.baseline_results    = results["baseline_results"]
            st.session_state.dataset_id          = results.get("dataset_id", "N/A")
            st.session_state.pipeline_duration_s = results.get("pipeline_duration_s", 0.0)
            st.session_state.provider_metadata   = results.get("provider_metadata", {})
            st.session_state.dataset_rows        = results.get("dataset_rows", 0)
            st.session_state.dataset_name        = results.get("dataset_name", "")
            st.session_state.dataset_signature   = results.get("dataset_signature", "")
            # Record what is now active so _dataset_changed() can compare later
            st.session_state.ACTIVE_DATASET      = AppState._current_dataset_key()
            st.session_state.ACTIVE_DATASET_SIG  = AppState._current_dataset_signature()
        else:
            st.session_state.raw_df           = None
            st.session_state.processed_df     = None
            st.session_state.pipeline_results = None
            st.session_state.fairness_warnings = []
            st.session_state.baseline_results = None
            st.session_state.dataset_rows     = 0

    @staticmethod
    def switch_dataset(new_filename: str = None, new_mode: str = None) -> None:
        """
        Switch the active dataset and invalidate all cached state.

        Call this from the Data Sources page when the user changes the
        dataset dropdown/mode and clicks Apply.
        """
        if new_mode:
            settings.data_mode = new_mode.upper()
        if new_filename and new_mode and new_mode.upper() == "CSV_DATA":
            settings.active_csv_dataset = new_filename
        elif new_mode and new_mode.upper() != "CSV_DATA":
            pass  # non-CSV modes don't need a filename

        AppState._clear_all_pipeline_state()

    # ------------------------------------------------------------------ #
    #  Canonical data accessors
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_pipeline_results():
        """Return the final scored/planned DataFrame."""
        return st.session_state.get("pipeline_results")

    @staticmethod
    def get_fairness_warnings():
        """Return the list of FairnessWarning objects."""
        return st.session_state.get("fairness_warnings", [])

    @staticmethod
    def get_baseline_results():
        """Return the BaselineRunResult from ."""
        return st.session_state.get("baseline_results")

    @staticmethod
    def get_pipeline_data():
        """Backward-compat alias → get_pipeline_results()."""
        return AppState.get_pipeline_results()

    @staticmethod
    def get_pipeline_result_dict():
        """Backward-compat alias → get_full_results()."""
        return AppState.get_full_results()

    @staticmethod
    def get_pipeline_run_id():
        """Return the dataset_id (governance registry key)."""
        return st.session_state.get("dataset_id")

    @staticmethod
    def get_active_dataset_info() -> dict:
        """
        Return metadata about the currently active dataset.
        Safe to call even before the pipeline has run.
        """
        return {
            "dataset_name":      st.session_state.get("dataset_name", settings.active_csv_dataset),
            "dataset_rows":      st.session_state.get("dataset_rows", 0),
            "dataset_signature": st.session_state.get("dataset_signature", ""),
            "data_mode":         settings.data_mode,
            "active_csv_dataset": settings.active_csv_dataset,
        }

    @staticmethod
    def get_system_health():
        """Return system health via SystemHealthService."""
        from src.services.system_health_service import SystemHealthService
        return SystemHealthService.get_system_health()

    @staticmethod
    def get_status() -> str:
        """Return the current app initialization status string."""
        return st.session_state.get("app_status", "UNINITIALIZED")

    @staticmethod
    def get_full_results() -> dict:
        """Return the full pipeline results dictionary consumed by validators."""
        if AppState.get_status() != "SUCCESS":
            return {
                "status": AppState.get_status(),
                "errors": st.session_state.get("app_errors", []),
            }
        return {
            "status":              "SUCCESS",
            "raw_df":              st.session_state.get("raw_df"),
            "processed_df":        st.session_state.get("processed_df"),
            "pipeline_results":    st.session_state.get("pipeline_results"),
            "fairness_warnings":   st.session_state.get("fairness_warnings", []),
            "baseline_results":    st.session_state.get("baseline_results"),
            "dataset_id":          st.session_state.get("dataset_id", "N/A"),
            "pipeline_duration_s": st.session_state.get("pipeline_duration_s", 0.0),
            "provider_metadata":   st.session_state.get("provider_metadata", {}),
            "dataset_name":        st.session_state.get("dataset_name", ""),
            "dataset_rows":        st.session_state.get("dataset_rows", 0),
            "errors": [],
        }

    # ------------------------------------------------------------------ #
    #  Error display helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def display_error_fallback() -> bool:
        """
        Show a professional error card when the pipeline has failed.
        Returns True if the fallback was shown (caller should st.stop()).
        """
        status = AppState.get_status()
        if status != "FAILED":
            return False

        st.error(" System Initialization Failed")
        errors = st.session_state.get("app_errors", [])
        for err in errors:
            st.markdown(
                f"""
                > **Reason:** {err}
                >
                > **Expected dataset:** `{settings.raw_data_dir}/{settings.active_csv_dataset}`
                >
                > Please verify the file exists and contains the required columns, then retry.
                """
            )

        if st.button("🔁 Retry Pipeline Initialization", type="primary"):
            AppState.initialize_application(force_refresh=True)
            st.rerun()
        return True
