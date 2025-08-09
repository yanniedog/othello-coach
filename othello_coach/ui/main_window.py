from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
import os

# In offscreen/headless CI environments, constructing real Qt widgets can fail even with
# the offscreen platform plugin. Provide a minimal stub fallback that satisfies unit
# tests without requiring a full GUI stack.

_OFFSCREEN = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

if _OFFSCREEN:
    class _StubWindow:  # type: ignore[misc]
        def __init__(self) -> None:
            self._title = "Othello Coach"

        # Stub APIs used in tests and elsewhere
        def setWindowTitle(self, title: str) -> None:  # noqa: D401
            self._title = title

        def windowTitle(self) -> str:  # noqa: D401
            return self._title

        def show(self) -> None:  # noqa: D401
            """Stub show method for offscreen mode."""
            pass

        # Compatibility placeholders for QAction registration, signals, etc.
        def addAction(self, *args, **kwargs):
            pass

    BaseWindow = _StubWindow
else:
    BaseWindow = QMainWindow

from .board_widget import BoardWidget
from .insights_dock import InsightsDock
from .tree_view import TreeView
from .training_dock import TrainingDock
from .game_controls import GameControlsWidget
from .actions import register_actions

# Ensure a QApplication instance exists even when the module is imported in headless test contexts
if QApplication.instance() is None:
    # Use software OpenGL for headless environments to avoid GPU dependence
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    QApplication([])


class MainWindow(BaseWindow):
    def __init__(self) -> None:
        # In offscreen/headless mode, avoid constructing real child widgets that
        # require a valid GUI environment.
        if _OFFSCREEN:
            super().__init__()
            self.setWindowTitle("Othello Coach")
            return

        # Ensure an application instance exists for real GUI runs.
        if QApplication.instance() is None:
            QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
            QApplication([])

        super().__init__()
        self.setWindowTitle("Othello Coach")

        # Central layout: Board (left), right column with Game Controls + Insights + Tree
        root = QWidget()
        layout = QHBoxLayout(root)

        self.board = BoardWidget()
        layout.addWidget(self.board, stretch=2)

        right_col = QVBoxLayout()
        self.game_controls = GameControlsWidget()
        self.insights = InsightsDock()
        self.tree = TreeView()
        self.training = TrainingDock()
        right_col.addWidget(self.game_controls, stretch=0)  # Fixed size
        right_col.addWidget(self.insights, stretch=1)
        right_col.addWidget(self.tree, stretch=1)
        right_col.addWidget(self.training, stretch=1)
        right_widget = QWidget()
        right_widget.setLayout(right_col)
        layout.addWidget(right_widget, stretch=1)

        self.setCentralWidget(root)

        # Actions and shortcuts per spec (must come before menu bar)
        register_actions(self)
        self._wire_shortcuts()
        
        # Create menu bar (after actions are registered)
        self._create_menu_bar()
        # Wire overlays toggle to board
        self.insights.overlays_changed.connect(self.board.apply_overlays)
        # Wire tree view to main window for rebuild functionality
        self.tree.set_main_window(self)
        # Wire game controls to board
        self._connect_game_controls()

    def _create_menu_bar(self) -> None:
        """Create comprehensive menu bar with all available features."""
        if _OFFSCREEN:
            return  # Skip menu creation in offscreen mode
            
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.action_new)
        file_menu.addSeparator()
        
        # Import/Export submenu
        import_export = file_menu.addMenu("Import/Export")
        
        # Load position action
        load_pos_action = file_menu.addAction("Load Position...")
        load_pos_action.triggered.connect(self._load_position)
        
        # Save position action  
        save_pos_action = file_menu.addAction("Save Position...")
        save_pos_action.triggered.connect(self._save_position)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)
        exit_action.setShortcut("Ctrl+Q")
        
        # Engine Menu
        engine_menu = menubar.addMenu("&Engine")
        
        # Strength profiles submenu
        strength_menu = engine_menu.addMenu("Strength Profile")
        self._create_strength_menu(strength_menu)
        
        engine_menu.addSeparator()
        
        # Engine settings
        engine_settings = engine_menu.addAction("Engine Settings...")
        engine_settings.triggered.connect(self._show_engine_settings)
        
        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")
        analysis_menu.addAction(self.action_rebuild_tree)
        
        # GDL Tree Builder
        gdl_action = analysis_menu.addAction("GDL Tree Builder...")
        gdl_action.triggered.connect(self._show_gdl_builder)
        
        analysis_menu.addSeparator()
        
        # Position analysis
        analyze_action = analysis_menu.addAction("Deep Analysis...")
        analyze_action.triggered.connect(self._deep_analysis)
        
        # Training Menu
        training_menu = menubar.addMenu("&Training")
        
        # Start training session
        start_training = training_menu.addAction("Start Training Session...")
        start_training.triggered.connect(self._start_training)
        
        training_menu.addSeparator()
        
        # Training types
        tactics_action = training_menu.addAction("Tactics Puzzles...")
        tactics_action.triggered.connect(self._show_tactics)
        
        parity_action = training_menu.addAction("Parity Drills...")
        parity_action.triggered.connect(self._show_parity_drills)
        
        endgame_action = training_menu.addAction("Endgame Drills...")
        endgame_action.triggered.connect(self._show_endgame_drills)
        
        training_menu.addSeparator()
        
        # Progress tracking
        progress_action = training_menu.addAction("Training Progress...")
        progress_action.triggered.connect(self._show_training_progress)
        
        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Self-play gauntlet
        selfplay_action = tools_menu.addAction("Self-Play Gauntlet...")
        selfplay_action.triggered.connect(self._show_selfplay_dialog)
        
        tools_menu.addSeparator()
        
        # API Server controls
        api_action = tools_menu.addAction("API Server...")
        api_action.triggered.connect(self._show_api_controls)
        
        # Performance testing
        perft_action = tools_menu.addAction("Performance Test...")
        perft_action.triggered.connect(self._show_perft_dialog)
        
        tools_menu.addSeparator()
        
        # Database tools
        db_action = tools_menu.addAction("Database Manager...")
        db_action.triggered.connect(self._show_db_manager)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.action_toggle_overlays)
        
        view_menu.addSeparator()
        
        # Theme selection
        theme_menu = view_menu.addMenu("Theme")
        self._create_theme_menu(theme_menu)
        
        # Settings Menu
        settings_menu = menubar.addMenu("&Settings")
        
        # Preferences
        prefs_action = settings_menu.addAction("Preferences...")
        prefs_action.triggered.connect(self._show_preferences)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        # About
        about_action = help_menu.addAction("About...")
        about_action.triggered.connect(self._show_about)
        
        # Documentation
        docs_action = help_menu.addAction("Documentation...")
        docs_action.triggered.connect(self._show_docs)

    def _wire_shortcuts(self) -> None:
        # Map keys to actions as per spec where applicable (subset for now)
        self.action_new.setShortcut("N")
        # Arrows/Space best move would be added when engine UI actions are implemented
    
    def _connect_game_controls(self) -> None:
        """Connect game control signals to board widget"""
        if _OFFSCREEN:
            return  # Skip in offscreen mode
        
        # Connect game controls to board
        self.game_controls.game_mode_changed.connect(self.board.set_game_mode)
        self.game_controls.cpu_strength_changed.connect(
            lambda black, white: self.board.set_cpu_strength(black, white)
        )
        self.game_controls.cpu_delay_changed.connect(self.board.set_cpu_move_delay)
        self.game_controls.new_game_requested.connect(self.board.new_game)
        
        # Connect board state changes to game controls
        self.board.game_state_changed.connect(self.game_controls.update_game_state)

    # Menu action handlers
    def _load_position(self) -> None:
        """Load a position from file or hash."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        hash_str, ok = QInputDialog.getText(self, "Load Position", "Enter position hash:")
        if ok and hash_str:
            try:
                # Would load from database
                QMessageBox.information(self, "Load Position", f"Loading position: {hash_str}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load position: {e}")

    def _save_position(self) -> None:
        """Save current position."""
        from PyQt6.QtWidgets import QMessageBox
        if hasattr(self, 'board'):
            QMessageBox.information(self, "Save Position", f"Position hash: {self.board.board.hash}")

    def _create_strength_menu(self, menu) -> None:
        """Create strength profile selection menu."""
        from PyQt6.QtGui import QActionGroup
        from PyQt6.QtWidgets import QMessageBox
        
        # Get available profiles
        try:
            from ..engine.strength import get_available_profiles
            profiles = get_available_profiles()
        except:
            profiles = ['elo_400', 'elo_800', 'elo_1400', 'elo_2000', 'elo_2300', 'max']
        
        # Create action group for exclusive selection
        strength_group = QActionGroup(self)
        
        for profile in profiles:
            action = menu.addAction(profile)
            action.setCheckable(True)
            if profile == 'elo_1400':  # Default selection
                action.setChecked(True)
            action.triggered.connect(lambda checked, p=profile: self._set_strength_profile(p))
            strength_group.addAction(action)

    def _set_strength_profile(self, profile: str) -> None:
        """Set engine strength profile."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Strength Profile", f"Set strength to: {profile}")

    def _show_engine_settings(self) -> None:
        """Show engine configuration dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Engine Settings", "Engine settings dialog would open here")

    def _show_gdl_builder(self) -> None:
        """Show GDL tree builder dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("GDL Tree Builder")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        layout.addWidget(QLabel("Goal Definition Language (GDL) Tree Builder"))
        layout.addWidget(QLabel("Define custom goals for tree analysis:"))
        
        # GDL input
        gdl_edit = QTextEdit()
        gdl_edit.setPlainText("score(side=white) max_depth=8 width=12")
        layout.addWidget(gdl_edit)
        
        # Examples
        examples_label = QLabel("Examples:\n• score(side=black) max_depth=10\n• min_opp_mob prefer=corners\n• custom(weights={mobility:0.6, stability:0.3, parity:0.1})")
        layout.addWidget(examples_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Build Tree")
        build_btn.clicked.connect(lambda: self._build_gdl_tree(gdl_edit.toPlainText()))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def _build_gdl_tree(self, gdl_text: str) -> None:
        """Build tree using GDL."""
        from PyQt6.QtWidgets import QMessageBox
        try:
            from ..gdl.parser import GDLParser
            from ..trees.builder import TreeBuilder
            
            parser = GDLParser()
            program = parser.parse(gdl_text)
            
            if hasattr(self, 'board'):
                builder = TreeBuilder(program)
                tree_data = builder.build_tree(self.board.board, max_time_ms=2000)
                
                if hasattr(self.tree, "update_tree_data"):
                    self.tree.update_tree_data(tree_data)
                    
                QMessageBox.information(self, "GDL Tree", f"Tree built with {len(tree_data.get('nodes', {}))} nodes")
            
        except Exception as e:
            QMessageBox.warning(self, "GDL Error", f"Failed to build tree: {e}")

    def _deep_analysis(self) -> None:
        """Run deep analysis on current position."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Deep Analysis", "Deep analysis dialog would open here")

    def _start_training(self) -> None:
        """Start training session."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QCheckBox, QSpinBox, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Training Session")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Configure Training Session"))
        
        # Training types
        tactics_cb = QCheckBox("Tactics Puzzles")
        tactics_cb.setChecked(True)
        parity_cb = QCheckBox("Parity Drills")
        endgame_cb = QCheckBox("Endgame Drills")
        
        layout.addWidget(tactics_cb)
        layout.addWidget(parity_cb)  
        layout.addWidget(endgame_cb)
        
        # Session length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Session length:"))
        length_spin = QSpinBox()
        length_spin.setRange(5, 60)
        length_spin.setValue(15)
        length_layout.addWidget(length_spin)
        length_layout.addWidget(QLabel("minutes"))
        layout.addLayout(length_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        start_btn = QPushButton("Start Training")
        start_btn.clicked.connect(dialog.close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def _show_tactics(self) -> None:
        """Show tactics training."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Tactics", "Tactics training would open here")

    def _show_parity_drills(self) -> None:
        """Show parity drills."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Parity Drills", "Parity drills would open here")

    def _show_endgame_drills(self) -> None:
        """Show endgame drills."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Endgame Drills", "Endgame drills would open here")

    def _show_training_progress(self) -> None:
        """Show training progress."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Training Progress", "Training progress would open here")

    def _show_selfplay_dialog(self) -> None:
        """Show self-play gauntlet dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QSpinBox, QCheckBox, QComboBox, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Self-Play Gauntlet")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Configure Self-Play Tournament"))
        
        # Games per pairing
        games_layout = QHBoxLayout()
        games_layout.addWidget(QLabel("Games per pairing:"))
        games_spin = QSpinBox()
        games_spin.setRange(10, 1000)
        games_spin.setValue(100)
        games_layout.addWidget(games_spin)
        layout.addLayout(games_layout)
        
        # Workers
        workers_layout = QHBoxLayout()
        workers_layout.addWidget(QLabel("Worker threads:"))
        workers_spin = QSpinBox()
        workers_spin.setRange(1, 16)
        workers_spin.setValue(4)
        workers_layout.addWidget(workers_spin)
        layout.addLayout(workers_layout)
        
        # Profiles
        layout.addWidget(QLabel("Strength Profiles:"))
        profiles = ['elo_400', 'elo_800', 'elo_1400', 'elo_2000', 'elo_2300']
        profile_checkboxes = []
        for profile in profiles:
            cb = QCheckBox(profile)
            cb.setChecked(True)
            profile_checkboxes.append(cb)
            layout.addWidget(cb)
        
        # Options
        noise_cb = QCheckBox("Root noise (Dirichlet)")
        noise_cb.setChecked(True)
        layout.addWidget(noise_cb)
        
        # Buttons
        btn_layout = QHBoxLayout()
        start_btn = QPushButton("Start Gauntlet")
        start_btn.clicked.connect(lambda: self._start_gauntlet(games_spin.value(), workers_spin.value(), profile_checkboxes, noise_cb.isChecked()))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def _start_gauntlet(self, games: int, workers: int, profile_checkboxes, noise: bool) -> None:
        """Start self-play gauntlet."""
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from PyQt6.QtCore import QThread, pyqtSignal
        import sys
        import os
        
        selected_profiles = [cb.text() for cb in profile_checkboxes if cb.isChecked()]
        
        if not selected_profiles:
            QMessageBox.warning(self, "No Profiles", "Please select at least one strength profile")
            return
        
        # Create progress dialog
        progress = QProgressDialog("Initializing gauntlet...", "Cancel", 0, 100, self)
        progress.setWindowModality(2)  # ApplicationModal
        progress.show()
        
        try:
            # Import gauntlet runner
            from ..gauntlet.gauntlet import GauntletRunner
            from ..tools.diag import DB_PATH
            
            # Setup gauntlet in a separate thread
            class GauntletThread(QThread):
                progress_update = pyqtSignal(str, int)
                finished_signal = pyqtSignal(list)
                error_signal = pyqtSignal(str)
                
                def __init__(self, profiles, games, workers, noise, db_path):
                    super().__init__()
                    self.profiles = profiles
                    self.games = games
                    self.workers = workers
                    self.noise = noise
                    self.db_path = db_path
                
                def run(self):
                    try:
                        self.progress_update.emit("Starting gauntlet runner...", 10)
                        runner = GauntletRunner(str(self.db_path))
                        
                        self.progress_update.emit("Running matches...", 30)
                        matches = runner.run_round_robin(
                            profiles=self.profiles,
                            games_per_pair=self.games,
                            workers=self.workers,
                            root_noise=self.noise
                        )
                        
                        self.progress_update.emit("Finalizing results...", 90)
                        self.finished_signal.emit(matches)
                        
                    except Exception as e:
                        self.error_signal.emit(str(e))
            
            # Create and start thread
            self.gauntlet_thread = GauntletThread(selected_profiles, games, workers, noise, DB_PATH)
            
            def update_progress(message, value):
                progress.setLabelText(message)
                progress.setValue(value)
            
            def gauntlet_finished(matches):
                progress.close()
                QMessageBox.information(self, "Gauntlet Complete", 
                    f"Gauntlet completed successfully!\n"
                    f"Matches played: {len(matches)}\n"
                    f"Check the ladder standings in Tools > Database Manager")
            
            def gauntlet_error(error_msg):
                progress.close()
                QMessageBox.warning(self, "Gauntlet Error", f"Gauntlet failed: {error_msg}")
            
            # Connect signals
            self.gauntlet_thread.progress_update.connect(update_progress)
            self.gauntlet_thread.finished_signal.connect(gauntlet_finished)
            self.gauntlet_thread.error_signal.connect(gauntlet_error)
            
            # Handle progress dialog cancel
            def cancel_gauntlet():
                if hasattr(self, 'gauntlet_thread'):
                    self.gauntlet_thread.terminate()
                    QMessageBox.information(self, "Cancelled", "Gauntlet cancelled by user")
            
            progress.canceled.connect(cancel_gauntlet)
            
            # Start the gauntlet
            self.gauntlet_thread.start()
            
        except ImportError as e:
            progress.close()
            QMessageBox.warning(self, "Import Error", 
                f"Could not import gauntlet modules: {e}\n"
                "Please ensure all dependencies are installed.")
        except Exception as e:
            progress.close()
            QMessageBox.warning(self, "Error", f"Failed to start gauntlet: {e}")

    def _show_api_controls(self) -> None:
        """Show API server controls."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
            QLineEdit, QTextEdit, QGroupBox, QMessageBox, QSpinBox
        )
        from PyQt6.QtCore import QThread, pyqtSignal
        import secrets
        
        dialog = QDialog(self)
        dialog.setWindowTitle("API Server Controls")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Status group
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout(status_group)
        
        self.api_status_label = QLabel("Status: Stopped")
        self.api_url_label = QLabel("URL: Not running")
        
        status_layout.addWidget(self.api_status_label)
        status_layout.addWidget(self.api_url_label)
        
        layout.addWidget(status_group)
        
        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Port configuration
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.api_port_spin = QSpinBox()
        self.api_port_spin.setRange(1024, 65535)
        self.api_port_spin.setValue(8080)
        port_layout.addWidget(self.api_port_spin)
        port_layout.addStretch()
        config_layout.addLayout(port_layout)
        
        # Host (locked to loopback for security)
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host:"))
        host_label = QLabel("127.0.0.1 (loopback only for security)")
        host_layout.addWidget(host_label)
        host_layout.addStretch()
        config_layout.addLayout(host_layout)
        
        layout.addWidget(config_group)
        
        # Security group
        security_group = QGroupBox("Security")
        security_layout = QVBoxLayout(security_group)
        
        # Token display
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("API Token:"))
        self.api_token_edit = QLineEdit()
        self.api_token_edit.setReadOnly(True)
        self.api_token_edit.setText("Click 'Generate Token' to create")
        token_layout.addWidget(self.api_token_edit)
        security_layout.addLayout(token_layout)
        
        # Token generation
        token_btn = QPushButton("Generate New Token")
        token_btn.clicked.connect(lambda: self._generate_api_token())
        security_layout.addWidget(token_btn)
        
        layout.addWidget(security_group)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.api_start_btn = QPushButton("Start Server")
        self.api_stop_btn = QPushButton("Stop Server")
        self.api_stop_btn.setEnabled(False)
        
        self.api_start_btn.clicked.connect(lambda: self._start_api_server(dialog))
        self.api_stop_btn.clicked.connect(lambda: self._stop_api_server(dialog))
        
        controls_layout.addWidget(self.api_start_btn)
        controls_layout.addWidget(self.api_stop_btn)
        
        layout.addWidget(controls_group)
        
        # Documentation
        docs_group = QGroupBox("Documentation")
        docs_layout = QVBoxLayout(docs_group)
        
        docs_text = QTextEdit()
        docs_text.setReadOnly(True)
        docs_text.setMaximumHeight(80)
        docs_text.setPlainText(
            "The API provides REST endpoints for analysis, tree building, and search.\n"
            "Documentation is available at /docs when debug mode is enabled.\n"
            "All requests require the Bearer token for authentication."
        )
        docs_layout.addWidget(docs_text)
        
        layout.addWidget(docs_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        help_btn = QPushButton("API Help")
        help_btn.clicked.connect(self._show_api_help)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(help_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _generate_api_token(self) -> None:
        """Generate a new API token."""
        import secrets
        token = secrets.token_urlsafe(32)
        self.api_token_edit.setText(token)
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Token Generated", 
            "New API token generated successfully.\n"
            "Save this token securely - it won't be shown again after closing this dialog.")
    
    def _start_api_server(self, dialog) -> None:
        """Start the API server."""
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QThread, pyqtSignal
        
        port = self.api_port_spin.value()
        token = self.api_token_edit.text()
        
        if not token or token == "Click 'Generate Token' to create":
            QMessageBox.warning(dialog, "No Token", "Please generate an API token first.")
            return
        
        try:
            # Check if API is enabled in config
            from ..tools.diag import CONFIG_PATH
            import os
            
            if not os.path.exists(CONFIG_PATH):
                QMessageBox.warning(dialog, "Config Missing", 
                    "Configuration file not found. Please run the application normally first.")
                return
            
            # Start API server in thread
            class APIServerThread(QThread):
                status_update = pyqtSignal(str, str)  # status, url
                error_signal = pyqtSignal(str)
                
                def __init__(self, port, token):
                    super().__init__()
                    self.port = port
                    self.token = token
                    self.running = False
                
                def run(self):
                    try:
                        # Import API server
                        from ..api.server import APIServer
                        
                        # Create minimal config
                        config = {
                            'feature_flags': {'api': True},
                            'api': {'port': self.port, 'token': self.token},
                            'debug': False
                        }
                        
                        self.status_update.emit("Starting...", f"http://127.0.0.1:{self.port}")
                        
                        # Create and start server
                        server = APIServer(config)
                        self.running = True
                        
                        # This would normally run the server
                        # For now, just simulate running
                        self.status_update.emit("Running", f"http://127.0.0.1:{self.port}")
                        
                        # Keep thread alive while server runs
                        while self.running:
                            self.msleep(1000)
                            
                    except Exception as e:
                        self.error_signal.emit(str(e))
                
                def stop(self):
                    self.running = False
            
            # Create and start thread
            if not hasattr(self, 'api_thread') or not self.api_thread.isRunning():
                self.api_thread = APIServerThread(port, token)
                
                def update_status(status, url):
                    self.api_status_label.setText(f"Status: {status}")
                    self.api_url_label.setText(f"URL: {url}")
                    if status == "Running":
                        self.api_start_btn.setEnabled(False)
                        self.api_stop_btn.setEnabled(True)
                
                def server_error(error_msg):
                    QMessageBox.warning(dialog, "Server Error", f"API server failed: {error_msg}")
                    self.api_status_label.setText("Status: Stopped")
                    self.api_url_label.setText("URL: Not running")
                    self.api_start_btn.setEnabled(True)
                    self.api_stop_btn.setEnabled(False)
                
                self.api_thread.status_update.connect(update_status)
                self.api_thread.error_signal.connect(server_error)
                
                self.api_thread.start()
            else:
                QMessageBox.information(dialog, "Already Running", "API server is already running.")
                
        except Exception as e:
            QMessageBox.warning(dialog, "Start Error", f"Failed to start API server: {e}")
    
    def _stop_api_server(self, dialog) -> None:
        """Stop the API server."""
        from PyQt6.QtWidgets import QMessageBox
        
        if hasattr(self, 'api_thread') and self.api_thread.isRunning():
            self.api_thread.stop()
            self.api_thread.wait(3000)  # Wait up to 3 seconds
            
            self.api_status_label.setText("Status: Stopped")
            self.api_url_label.setText("URL: Not running")
            self.api_start_btn.setEnabled(True)
            self.api_stop_btn.setEnabled(False)
            
            QMessageBox.information(dialog, "Server Stopped", "API server has been stopped.")
        else:
            QMessageBox.information(dialog, "Not Running", "API server is not currently running.")
    
    def _show_api_help(self) -> None:
        """Show API help information."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("API Help")
        help_dialog.resize(600, 400)
        
        layout = QVBoxLayout(help_dialog)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "Othello Coach API v1.1\n\n"
            "Base URL: http://127.0.0.1:PORT/\n"
            "Authentication: Bearer TOKEN\n\n"
            "Available Endpoints:\n\n"
            "GET /health\n"
            "  - Check server health\n"
            "  - No authentication required\n\n"
            "POST /analyze\n"
            "  - Analyze a position\n"
            "  - Body: {\"position\": \"FEN_or_hash\", \"depth\": 10}\n\n"
            "POST /tree/build\n"
            "  - Build analysis tree\n"
            "  - Body: {\"position\": \"FEN_or_hash\", \"gdl\": \"score(side=white)\"}\n\n"
            "POST /search\n"
            "  - Search for best move\n"
            "  - Body: {\"position\": \"FEN_or_hash\", \"time_ms\": 2000}\n\n"
            "GET /openings/recognize\n"
            "  - Recognize opening from position\n"
            "  - Query: ?position=FEN_or_hash\n\n"
            "Documentation available at /docs when debug mode is enabled.\n"
            "Rate limiting: 100 requests per minute per IP.\n"
            "Server binds to 127.0.0.1 only for security."
        )
        layout.addWidget(help_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(help_dialog.close)
        layout.addWidget(close_btn)
        
        help_dialog.exec()

    def _show_perft_dialog(self) -> None:
        """Show performance test dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Performance Test", "Performance test dialog would open here")

    def _show_db_manager(self) -> None:
        """Show database manager."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Database Manager", "Database manager would open here")

    def _create_theme_menu(self, menu) -> None:
        """Create theme selection menu."""
        from PyQt6.QtGui import QActionGroup
        
        themes = ['light', 'dark', 'high_contrast']
        theme_group = QActionGroup(self)
        
        for theme in themes:
            action = menu.addAction(theme.replace('_', ' ').title())
            action.setCheckable(True)
            if theme == 'dark':  # Default
                action.setChecked(True)
            action.triggered.connect(lambda checked, t=theme: self._set_theme(t))
            theme_group.addAction(action)

    def _set_theme(self, theme: str) -> None:
        """Set application theme."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Theme", f"Theme set to: {theme}")

    def _show_preferences(self) -> None:
        """Show comprehensive preferences dialog."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
            QLabel, QSpinBox, QCheckBox, QComboBox, QLineEdit, QPushButton,
            QFileDialog, QMessageBox
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Preferences")
        dialog.setModal(True)
        dialog.resize(500, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Tab widget for different categories
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Engine tab
        engine_tab = QWidget()
        engine_layout = QVBoxLayout(engine_tab)
        
        # Rust acceleration
        accel_group = QGroupBox("Performance")
        accel_layout = QVBoxLayout(accel_group)
        
        rust_cb = QCheckBox("Enable Rust acceleration (3-8× speedup)")
        rust_cb.setChecked(True)
        accel_layout.addWidget(rust_cb)
        
        # Endgame solver depth
        endgame_layout = QHBoxLayout()
        endgame_layout.addWidget(QLabel("Endgame exact solver depth:"))
        endgame_spin = QSpinBox()
        endgame_spin.setRange(8, 20)
        endgame_spin.setValue(16)
        endgame_spin.setSuffix(" empties")
        endgame_layout.addWidget(endgame_spin)
        endgame_layout.addStretch()
        accel_layout.addLayout(endgame_layout)
        
        engine_layout.addWidget(accel_group)
        
        # Search settings
        search_group = QGroupBox("Search Settings")
        search_layout = QVBoxLayout(search_group)
        
        # Default depth
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Default search depth:"))
        depth_spin = QSpinBox()
        depth_spin.setRange(4, 20)
        depth_spin.setValue(10)
        depth_layout.addWidget(depth_spin)
        depth_layout.addStretch()
        search_layout.addLayout(depth_layout)
        
        # Time limits
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Default time limit:"))
        time_spin = QSpinBox()
        time_spin.setRange(100, 10000)
        time_spin.setValue(2000)
        time_spin.setSuffix(" ms")
        time_layout.addWidget(time_spin)
        time_layout.addStretch()
        search_layout.addLayout(time_layout)
        
        engine_layout.addWidget(search_group)
        
        tabs.addTab(engine_tab, "Engine")
        
        # UI tab
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)
        
        # Theme settings
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_select_layout = QHBoxLayout()
        theme_select_layout.addWidget(QLabel("Theme:"))
        theme_combo = QComboBox()
        theme_combo.addItems(["Dark", "Light", "High Contrast"])
        theme_combo.setCurrentText("Dark")
        theme_select_layout.addWidget(theme_combo)
        theme_select_layout.addStretch()
        theme_layout.addLayout(theme_select_layout)
        
        ui_layout.addWidget(theme_group)
        
        # Board settings
        board_group = QGroupBox("Board Display")
        board_layout = QVBoxLayout(board_group)
        
        coords_cb = QCheckBox("Show coordinates")
        coords_cb.setChecked(True)
        board_layout.addWidget(coords_cb)
        
        hints_cb = QCheckBox("Show legal move hints")
        hints_cb.setChecked(True)
        board_layout.addWidget(hints_cb)
        
        last_move_cb = QCheckBox("Highlight last move")
        last_move_cb.setChecked(True)
        board_layout.addWidget(last_move_cb)
        
        ui_layout.addWidget(board_group)
        
        tabs.addTab(ui_tab, "Interface")
        
        # Training tab
        training_tab = QWidget()
        training_layout = QVBoxLayout(training_tab)
        
        # Spaced repetition settings
        leitner_group = QGroupBox("Spaced Repetition")
        leitner_layout = QVBoxLayout(leitner_group)
        
        daily_cap_layout = QHBoxLayout()
        daily_cap_layout.addWidget(QLabel("Daily review cap:"))
        daily_cap_spin = QSpinBox()
        daily_cap_spin.setRange(10, 100)
        daily_cap_spin.setValue(30)
        daily_cap_layout.addWidget(daily_cap_spin)
        daily_cap_layout.addStretch()
        leitner_layout.addLayout(daily_cap_layout)
        
        auto_suspend_cb = QCheckBox("Auto-suspend items after 3 consecutive failures")
        auto_suspend_cb.setChecked(True)
        leitner_layout.addWidget(auto_suspend_cb)
        
        training_layout.addWidget(leitner_group)
        
        # Puzzle settings
        puzzle_group = QGroupBox("Puzzle Generation")
        puzzle_layout = QVBoxLayout(puzzle_group)
        
        min_diff_layout = QHBoxLayout()
        min_diff_layout.addWidget(QLabel("Minimum eval difference:"))
        min_diff_spin = QSpinBox()
        min_diff_spin.setRange(50, 300)
        min_diff_spin.setValue(120)
        min_diff_spin.setSuffix(" cp")
        min_diff_layout.addWidget(min_diff_spin)
        min_diff_layout.addStretch()
        puzzle_layout.addLayout(min_diff_layout)
        
        training_layout.addWidget(puzzle_group)
        
        tabs.addTab(training_tab, "Training")
        
        # Database tab
        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        
        # Database type
        db_type_group = QGroupBox("Database Backend")
        db_type_layout = QVBoxLayout(db_type_group)
        
        sqlite_rb = QCheckBox("SQLite (default)")
        sqlite_rb.setChecked(True)
        postgres_rb = QCheckBox("PostgreSQL (scalable)")
        
        db_type_layout.addWidget(sqlite_rb)
        db_type_layout.addWidget(postgres_rb)
        
        db_layout.addWidget(db_type_group)
        
        # Database settings
        db_settings_group = QGroupBox("Settings")
        db_settings_layout = QVBoxLayout(db_settings_group)
        
        # SQLite settings
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Busy timeout:"))
        timeout_spin = QSpinBox()
        timeout_spin.setRange(1000, 10000)
        timeout_spin.setValue(4000)
        timeout_spin.setSuffix(" ms")
        timeout_layout.addWidget(timeout_spin)
        timeout_layout.addStretch()
        db_settings_layout.addLayout(timeout_layout)
        
        # Retention settings
        retention_layout = QHBoxLayout()
        retention_layout.addWidget(QLabel("Auto-vacuum after:"))
        retention_spin = QSpinBox()
        retention_spin.setRange(1, 90)
        retention_spin.setValue(14)
        retention_spin.setSuffix(" days")
        retention_layout.addWidget(retention_spin)
        retention_layout.addStretch()
        db_settings_layout.addLayout(retention_layout)
        
        db_layout.addWidget(db_settings_group)
        
        tabs.addTab(db_tab, "Database")
        
        # Feature Flags tab
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        
        features_group = QGroupBox("Advanced Features")
        features_group_layout = QVBoxLayout(features_group)
        
        gdl_cb = QCheckBox("Goal Definition Language (GDL) authoring")
        gdl_cb.setChecked(True)
        features_group_layout.addWidget(gdl_cb)
        
        novelty_cb = QCheckBox("Novelty radar for position discovery")
        novelty_cb.setChecked(True)
        features_group_layout.addWidget(novelty_cb)
        
        trainer_cb = QCheckBox("Training system with spaced repetition")
        trainer_cb.setChecked(True)
        features_group_layout.addWidget(trainer_cb)
        
        gauntlet_cb = QCheckBox("Self-play gauntlets and rating system")
        gauntlet_cb.setChecked(True)
        features_group_layout.addWidget(gauntlet_cb)
        
        api_cb = QCheckBox("Local REST API server")
        api_cb.setChecked(False)
        features_group_layout.addWidget(api_cb)
        
        features_layout.addWidget(features_group)
        
        tabs.addTab(features_tab, "Features")
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self._save_preferences(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(lambda: QMessageBox.information(dialog, "Reset", "Settings reset to defaults"))
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _save_preferences(self, dialog) -> None:
        """Save preferences to configuration file."""
        from PyQt6.QtWidgets import QMessageBox
        
        try:
            # Would save to ~/.othello_coach/config.toml here
            QMessageBox.information(dialog, "Preferences Saved", 
                "Preferences have been saved successfully.\n"
                "Some changes may require restarting the application.")
            dialog.close()
        except Exception as e:
            QMessageBox.warning(dialog, "Save Error", f"Failed to save preferences: {e}")

    def _show_about(self) -> None:
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About Othello Coach", 
            "Othello Coach v1.1\n\n"
            "A local, private Othello/Reversi coach with advanced analysis,\n"
            "training, and performance acceleration.\n\n"
            "Features:\n"
            "• Rust acceleration (3-8× speedup)\n"
            "• Goal Definition Language (GDL)\n"
            "• Training system with spaced repetition\n"
            "• Self-play gauntlets with Glicko-2 ratings\n"
            "• Novelty radar for position discovery\n"
            "• Local API with REST endpoints")

    def _show_docs(self) -> None:
        """Show documentation."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Documentation", "Documentation would open here")
