import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from config.current import AppConfig
from frontend import controls_panel
from frontend.controls_panel import ControlsPanel
from frontend.main_window import MainWindow


def test_controls_panel_restores_saved_settings(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        controls_panel,
        "available_audio_output_devices",
        lambda: [(4, "USB headphones")],
    )
    settings_path = tmp_path / "receiver.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    first = ControlsPanel(AppConfig(), settings_store=settings)

    first.source_combo.setCurrentIndex(first.source_combo.findData("synthetic"))
    first.frequency_spin.setValue(101_700_000)
    first.ppm_spin.setValue(12)
    first.audio_output_combo.setCurrentIndex(first.audio_output_combo.findData(4))
    settings.sync()

    restored = ControlsPanel(
        AppConfig(),
        settings_store=QSettings(str(settings_path), QSettings.Format.IniFormat),
    )

    assert restored.current_settings()["source"] == "synthetic"
    assert restored.current_settings()["center_frequency"] == 101_700_000
    assert restored.current_settings()["ppm_correction"] == 12
    assert restored.current_settings()["audio_output_device"] == 4
    first.close()
    restored.close()
    app.processEvents()


def test_controls_panel_reset_defaults_persists_default_settings(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        controls_panel,
        "available_audio_output_devices",
        lambda: [(4, "USB headphones")],
    )
    settings_path = tmp_path / "receiver.ini"
    panel = ControlsPanel(
        AppConfig(),
        settings_store=QSettings(str(settings_path), QSettings.Format.IniFormat),
    )

    panel.source_combo.setCurrentIndex(panel.source_combo.findData("synthetic"))
    panel.frequency_spin.setValue(101_700_000)
    panel.ppm_spin.setValue(12)
    panel.audio_output_combo.setCurrentIndex(panel.audio_output_combo.findData(4))

    panel.reset_defaults_button.click()
    panel._settings_store.sync()

    assert panel.current_settings()["source"] == "rtl_sdr"
    assert panel.current_settings()["center_frequency"] == 100_000_000
    assert panel.current_settings()["ppm_correction"] == 0
    assert panel.current_settings()["audio_output_device"] is None

    restored = ControlsPanel(
        AppConfig(),
        settings_store=QSettings(str(settings_path), QSettings.Format.IniFormat),
    )

    assert restored.current_settings()["source"] == "rtl_sdr"
    assert restored.current_settings()["center_frequency"] == 100_000_000
    assert restored.current_settings()["ppm_correction"] == 0
    assert restored.current_settings()["audio_output_device"] is None
    panel.close()
    restored.close()
    app.processEvents()


def test_main_window_source_label_matches_selected_source():
    synthetic = type("WindowState", (), {"settings": {"source": "synthetic"}})()
    rtl_sdr = type("WindowState", (), {"settings": {"source": "rtl_sdr"}})()

    assert MainWindow._source_label(synthetic) == "Synthetic"
    assert MainWindow._source_label(rtl_sdr) == "RTL-SDR"


def test_main_window_controls_open_in_a_separate_window():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(AppConfig())
    window.show()
    app.processEvents()
    display_width = window.centralWidget().width()

    assert not window.controls_window.isVisible()
    assert not window.controls_button.isChecked()

    window.controls_button.click()
    app.processEvents()

    assert window.controls_window.isVisible()
    assert window.controls_button.isChecked()
    assert window.centralWidget().width() == display_width

    window.controls_window.close()
    app.processEvents()

    assert not window.controls_window.isVisible()
    assert not window.controls_button.isChecked()
    window.close()
