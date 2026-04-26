"""Settings dialog: hotkey, backend, model, language, auto-paste.

Opens from the tray menu. On Save, writes the new config to disk and
returns the updated Config so the controller can rebind the hotkey and
drop the cached transcriber (it'll re-load on the next press).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from . import config as config_mod
from .hotkey_recorder import HotkeyRecorder

# Curated lists — keep small; users can hand-edit the TOML for exotic values.
BACKENDS = ["local", "openai"]
LOCAL_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = [
    ("auto", "Auto-detect"),
    ("en", "English"),
    ("zh", "Chinese"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
]


class SettingsDialog(QDialog):
    def __init__(self, cfg: config_mod.Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Murmur — Settings")
        self.setMinimumWidth(420)
        self._cfg = cfg

        form = QFormLayout()

        self.hotkey_recorder = HotkeyRecorder(cfg.hotkey)
        form.addRow("Hotkey:", self.hotkey_recorder)
        form.addRow(
            "",
            QLabel(
                "Click Record, then press the key (or combo) you want as "
                "your push-to-talk."
            ),
        )

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(BACKENDS)
        self.backend_combo.setCurrentText(cfg.backend)
        form.addRow("Backend:", self.backend_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItems(LOCAL_MODELS)
        if cfg.local.model in LOCAL_MODELS:
            self.model_combo.setCurrentText(cfg.local.model)
        else:
            self.model_combo.addItem(cfg.local.model)
            self.model_combo.setCurrentText(cfg.local.model)
        form.addRow("Local model:", self.model_combo)

        self.language_combo = QComboBox()
        for code, label in LANGUAGES:
            self.language_combo.addItem(f"{label} ({code})", userData=code)
        idx = next(
            (i for i, (code, _) in enumerate(LANGUAGES) if code == cfg.language),
            0,
        )
        self.language_combo.setCurrentIndex(idx)
        form.addRow("Language:", self.language_combo)

        self.api_key_env = QLineEdit(cfg.openai.api_key_env)
        form.addRow("OpenAI API key env var:", self.api_key_env)

        self.auto_paste = QCheckBox(
            "Auto-paste at cursor (uncheck = clipboard only)"
        )
        self.auto_paste.setChecked(cfg.auto_paste)
        form.addRow("", self.auto_paste)

        self.show_hud = QCheckBox("Show recording HUD")
        self.show_hud.setChecked(cfg.show_hud)
        form.addRow("", self.show_hud)

        layout = QVBoxLayout(self)
        layout.addLayout(form)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def updated_config(self) -> config_mod.Config:
        """Build a Config from the current widget values."""
        new = config_mod.Config(
            backend=self.backend_combo.currentText(),
            language=self.language_combo.currentData(),
            hotkey=self.hotkey_recorder.value() or self._cfg.hotkey,
            auto_paste=self.auto_paste.isChecked(),
            show_hud=self.show_hud.isChecked(),
            local=config_mod.LocalBackendConfig(
                model=self.model_combo.currentText(),
                device=self._cfg.local.device,
                compute_type=self._cfg.local.compute_type,
            ),
            openai=config_mod.OpenAIBackendConfig(
                api_key_env=self.api_key_env.text().strip()
                or self._cfg.openai.api_key_env,
                model=self._cfg.openai.model,
            ),
        )
        return new
