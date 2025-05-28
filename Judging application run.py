import sys
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QGroupBox, QGridLayout, QHeaderView, QFrame, QScrollArea,
    QProgressBar, QCheckBox, QInputDialog, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QPalette, QColor


@dataclass
class Rider:
    """Represents a rider in the competition"""
    id: int
    name: str
    age: int
    gender: str
    discipline: str = ""
    category: str = ""
    run1_scores: List[float] = None
    run2_scores: List[float] = None
    final_score: float = 0.0
    
    def __post_init__(self):
        # Initialize scores based on number of judges
        if self.run1_scores is None:
            self.run1_scores = []
        if self.run2_scores is None:
            self.run2_scores = []
    
    def calculate_final_score(self):
        """Calculate final score as average of best run"""
        run1_avg = sum(self.run1_scores) / len(self.run1_scores) if self.run1_scores else 0
        run2_avg = sum(self.run2_scores) / len(self.run2_scores) if self.run2_scores else 0
        self.final_score = max(run1_avg, run2_avg)
        return self.final_score
    
    def to_dict(self):
        """Convert rider to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'discipline': self.discipline,
            'category': self.category,
            'run1_scores': self.run1_scores,
            'run2_scores': self.run2_scores,
            'final_score': self.final_score
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create rider from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            discipline=data.get('discipline', ''),
            category=data.get('category', ''),
            run1_scores=data.get('run1_scores', []),
            run2_scores=data.get('run2_scores', []),
            final_score=data.get('final_score', 0.0)
        )


class CategoryManager:
    """Manages competition categories"""
    
    def __init__(self):
        self.categories = {
            "PARK": [
                "7 and Under",
                "10 and Under", 
                "13 and Under",
                "15 and Under",
                "17 and Under",
                "Open Men",
                "Pro Men",
                "Junior Women",
                "Open Women",
                "Pro Women"
            ],
            "STREET": [
                "Junior Street",
                "Open Street"
            ]
        }
    
    def get_all_categories(self):
        """Get all categories as a flat list with discipline prefix"""
        all_cats = []
        for discipline, cats in self.categories.items():
            for cat in cats:
                all_cats.append(f"{discipline} - {cat}")
        return all_cats
    
    def get_all_categories_simple(self):
        """Get all categories as a flat list without discipline prefix"""
        all_cats = []
        for discipline, cats in self.categories.items():
            all_cats.extend(cats)
        return all_cats
    
    def get_categories_by_discipline(self, discipline):
        """Get categories for a specific discipline"""
        return self.categories.get(discipline, [])
    
    def add_category(self, discipline, category):
        """Add a new category to a discipline"""
        if discipline not in self.categories:
            self.categories[discipline] = []
        if category not in self.categories[discipline]:
            self.categories[discipline].append(category)
    
    def remove_category(self, discipline, category):
        """Remove a category from a discipline"""
        if discipline in self.categories and category in self.categories[discipline]:
            self.categories[discipline].remove(category)
    
    def add_discipline(self, discipline):
        """Add a new discipline"""
        if discipline not in self.categories:
            self.categories[discipline] = []
    
    def remove_discipline(self, discipline):
        """Remove a discipline"""
        if discipline in self.categories:
            del self.categories[discipline]
    
    def get_disciplines(self):
        """Get list of all disciplines"""
        return list(self.categories.keys())
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return self.categories
    
    def from_dict(self, data):
        """Load from dictionary"""
        self.categories = data


class CategoryDialog(QDialog):
    """Dialog for managing categories"""
    
    def __init__(self, category_manager, parent=None):
        super().__init__(parent)
        self.category_manager = category_manager
        self.setup_ui()
        self.load_categories()
    
    def setup_ui(self):
        self.setWindowTitle("Manage Categories")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # Discipline management
        discipline_group = QGroupBox("Disciplines")
        discipline_layout = QVBoxLayout()
        
        discipline_controls = QHBoxLayout()
        self.discipline_combo = QComboBox()
        self.discipline_combo.currentTextChanged.connect(self.load_discipline_categories)
        discipline_controls.addWidget(QLabel("Discipline:"))
        discipline_controls.addWidget(self.discipline_combo)
        
        self.new_discipline_edit = QLineEdit()
        self.new_discipline_edit.setPlaceholderText("New discipline name")
        add_discipline_btn = QPushButton("Add Discipline")
        add_discipline_btn.clicked.connect(self.add_discipline)
        
        discipline_controls.addWidget(self.new_discipline_edit)
        discipline_controls.addWidget(add_discipline_btn)
        
        remove_discipline_btn = QPushButton("Remove Discipline")
        remove_discipline_btn.clicked.connect(self.remove_discipline)
        discipline_controls.addWidget(remove_discipline_btn)
        
        discipline_layout.addLayout(discipline_controls)
        discipline_group.setLayout(discipline_layout)
        layout.addWidget(discipline_group)
        
        # Category management
        category_group = QGroupBox("Categories")
        category_layout = QVBoxLayout()
        
        category_controls = QHBoxLayout()
        self.new_category_edit = QLineEdit()
        self.new_category_edit.setPlaceholderText("New category name")
        add_category_btn = QPushButton("Add Category")
        add_category_btn.clicked.connect(self.add_category)
        remove_category_btn = QPushButton("Remove Category")
        remove_category_btn.clicked.connect(self.remove_category)
        
        category_controls.addWidget(self.new_category_edit)
        category_controls.addWidget(add_category_btn)
        category_controls.addWidget(remove_category_btn)
        category_layout.addLayout(category_controls)
        
        # Categories list
        self.categories_list = QTableWidget()
        self.categories_list.setColumnCount(1)
        self.categories_list.setHorizontalHeaderLabels(["Categories"])
        self.categories_list.horizontalHeader().setStretchLastSection(True)
        category_layout.addWidget(self.categories_list)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_categories(self):
        """Load disciplines into combo box"""
        self.discipline_combo.clear()
        self.discipline_combo.addItems(self.category_manager.get_disciplines())
    
    def load_discipline_categories(self, discipline):
        """Load categories for selected discipline"""
        if not discipline:
            self.categories_list.setRowCount(0)
            return
        
        categories = self.category_manager.get_categories_by_discipline(discipline)
        self.categories_list.setRowCount(len(categories))
        
        for row, category in enumerate(categories):
            self.categories_list.setItem(row, 0, QTableWidgetItem(category))
    
    def add_discipline(self):
        """Add new discipline"""
        name = self.new_discipline_edit.text().strip()
        if name and name not in self.category_manager.get_disciplines():
            self.category_manager.add_discipline(name)
            self.load_categories()
            self.discipline_combo.setCurrentText(name)
            self.new_discipline_edit.clear()
    
    def remove_discipline(self):
        """Remove selected discipline"""
        current_discipline = self.discipline_combo.currentText()
        if current_discipline:
            reply = QMessageBox.question(
                self, "Confirm Removal",
                f"Remove discipline '{current_discipline}' and all its categories?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.category_manager.remove_discipline(current_discipline)
                self.load_categories()
    
    def add_category(self):
        """Add new category to current discipline"""
        current_discipline = self.discipline_combo.currentText()
        category_name = self.new_category_edit.text().strip()
        
        if current_discipline and category_name:
            self.category_manager.add_category(current_discipline, category_name)
            self.load_discipline_categories(current_discipline)
            self.new_category_edit.clear()
    
    def remove_category(self):
        """Remove selected category"""
        current_discipline = self.discipline_combo.currentText()
        current_row = self.categories_list.currentRow()
        
        if current_discipline and current_row >= 0:
            category_name = self.categories_list.item(current_row, 0).text()
            reply = QMessageBox.question(
                self, "Confirm Removal",
                f"Remove category '{category_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.category_manager.remove_category(current_discipline, category_name)
                self.load_discipline_categories(current_discipline)


class RiderDialog(QDialog):
    """Dialog for adding/editing riders"""

    def __init__(self, category_manager, rider=None, parent=None):
        super().__init__(parent)
        self.rider = rider
        self.category_manager = category_manager
        self.setup_ui()
        
        if rider:
            self.populate_fields()
    
    def setup_ui(self):
        self.setWindowTitle("Add/Edit Rider")
        self.setModal(True)
        self.resize(400, 350)
        
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.age_spin = QSpinBox()
        self.age_spin.setRange(5, 99)
        self.age_spin.setValue(15)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])
        
        # Discipline selection
        self.discipline_combo = QComboBox()
        self.discipline_combo.addItems(self.category_manager.get_disciplines())
        self.discipline_combo.currentTextChanged.connect(self.update_categories)
        
        # Category selection
        self.category_combo = QComboBox()
        
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Age:", self.age_spin)
        layout.addRow("Gender:", self.gender_combo)
        layout.addRow("Discipline:", self.discipline_combo)
        layout.addRow("Category:", self.category_combo)
        
        # Initialize categories for first discipline
        if self.category_manager.get_disciplines():
            self.update_categories(self.category_manager.get_disciplines()[0])
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        
        self.setLayout(main_layout)
    
    def update_categories(self, discipline):
        """Update available categories based on selected discipline"""
        self.category_combo.clear()
        if discipline:
            categories = self.category_manager.get_categories_by_discipline(discipline)
            self.category_combo.addItems(categories)
    
    def populate_fields(self):
        """Populate fields with existing rider data"""
        if self.rider:
            self.name_edit.setText(self.rider.name)
            self.age_spin.setValue(self.rider.age)
            self.gender_combo.setCurrentText(self.rider.gender)
            self.discipline_combo.setCurrentText(self.rider.discipline)
            # This will trigger update_categories and then we can set the category
            self.category_combo.setCurrentText(self.rider.category)
    
    def get_rider_data(self):
        """Get rider data from form"""
        return {
            'name': self.name_edit.text(),
            'age': self.age_spin.value(),
            'gender': self.gender_combo.currentText(),
            'discipline': self.discipline_combo.currentText(),
            'category': self.category_combo.currentText()
        }


class JudgeScoreWidget(QWidget):
    """Simple widget for judge scoring"""
    
    score_updated = Signal(int, int, float)  # rider_id, judge_number, score
    
    def __init__(self, judge_number, parent=None):
        super().__init__(parent)
        self.judge_number = judge_number
        self.current_rider_id = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Judge label
        judge_label = QLabel(f"Judge {self.judge_number + 1}")
        judge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        judge_label.setFont(font)
        layout.addWidget(judge_label)
        
        # Score input
        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0.0, 100.0)
        self.score_spin.setDecimals(1)
        self.score_spin.setSingleStep(0.5)
        self.score_spin.setMinimumHeight(40)
        font = QFont()
        font.setPointSize(14)
        self.score_spin.setFont(font)
        self.score_spin.valueChanged.connect(self.on_score_changed)
        layout.addWidget(self.score_spin)
        
        layout.addWidget(QLabel("Score (0-100)"))
        
        self.setLayout(layout)
        self.setFixedWidth(120)
    
    def set_rider(self, rider_id):
        self.current_rider_id = rider_id
    
    def set_score(self, score):
        self.score_spin.setValue(score)
    
    def on_score_changed(self):
        if self.current_rider_id is not None:
            score = self.score_spin.value()
            self.score_updated.emit(self.current_rider_id, self.judge_number, score)


class CompetitionManager:
    """Manages competition data and operations"""
    
    def __init__(self):
        self.riders: Dict[int, Rider] = {}
        self.next_id = 1
        self.competition_name = "Freestyle Scooter Competition"
        self.competition_date = datetime.now().strftime("%Y-%m-%d")
        self.category_manager = CategoryManager()
        self.num_judges = 3  # Default number of judges
        self.timer_duration = 45  # Default timer duration in seconds
    
    def add_rider(self, name, age, gender, discipline="", category=""):
        """Add a new rider"""
        rider = Rider(
            id=self.next_id,
            name=name,
            age=age,
            gender=gender,
            discipline=discipline,
            category=category
        )
        # Initialize scores for the current number of judges
        rider.run1_scores = [0.0] * self.num_judges
        rider.run2_scores = [0.0] * self.num_judges
        
        self.riders[self.next_id] = rider
        self.next_id += 1
        return rider
    
    def update_rider(self, rider_id, **kwargs):
        """Update rider information"""
        if rider_id in self.riders:
            rider = self.riders[rider_id]
            for key, value in kwargs.items():
                if hasattr(rider, key):
                    setattr(rider, key, value)
    
    def remove_rider(self, rider_id):
        """Remove a rider"""
        if rider_id in self.riders:
            del self.riders[rider_id]
    
    def get_categories_with_riders(self):
        """Get all categories that have riders, organized by discipline"""
        categories_with_riders = {}
        for rider in self.riders.values():
            discipline = rider.discipline or "Unassigned"
            category = rider.category or "Unassigned"
            full_category = f"{discipline} - {category}" if discipline != "Unassigned" else category
            
            if full_category not in categories_with_riders:
                categories_with_riders[full_category] = []
            categories_with_riders[full_category].append(rider)
        
        # Sort riders in each category by name
        for category_riders in categories_with_riders.values():
            category_riders.sort(key=lambda r: r.name)
        
        return categories_with_riders
    
    def get_disciplines_with_riders(self):
        """Get all disciplines that have riders"""
        disciplines_with_riders = {}
        for rider in self.riders.values():
            discipline = rider.discipline or "Unassigned"
            if discipline not in disciplines_with_riders:
                disciplines_with_riders[discipline] = []
            disciplines_with_riders[discipline].append(rider)
        
        # Sort riders in each discipline by category then name
        for discipline_riders in disciplines_with_riders.values():
            discipline_riders.sort(key=lambda r: (r.category, r.name))
        
        return disciplines_with_riders
    
    def update_score(self, rider_id, run_number, judge_number, score):
        """Update a rider's score"""
        if rider_id in self.riders:
            rider = self.riders[rider_id]
            if run_number == 1:
                if judge_number < len(rider.run1_scores):
                    rider.run1_scores[judge_number] = score
            elif run_number == 2:
                if judge_number < len(rider.run2_scores):
                    rider.run2_scores[judge_number] = score
            rider.calculate_final_score()
    
    def clear_all(self):
        """Clear all competition data"""
        self.riders.clear()
        self.next_id = 1
        self.competition_name = "Freestyle Scooter Competition"
        self.competition_date = datetime.now().strftime("%Y-%m-%d")
        # Don't reset categories or judge settings
    
    def save_event(self, filename):
        """Save the entire event to a JSON file"""
        event_data = {
            'version': '1.0',
            'competition_name': self.competition_name,
            'competition_date': self.competition_date,
            'num_judges': self.num_judges,
            'timer_duration': self.timer_duration,
            'next_id': self.next_id,
            'categories': self.category_manager.to_dict(),
            'riders': [rider.to_dict() for rider in self.riders.values()]
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(event_data, f, indent=2)
            return True
        except Exception as e:
            return False, str(e)
    
    def load_event(self, filename):
        """Load an entire event from a JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            # Clear existing data
            self.clear_all()
            
            # Load event metadata
            self.competition_name = event_data.get('competition_name', 'Freestyle Scooter Competition')
            self.competition_date = event_data.get('competition_date', datetime.now().strftime("%Y-%m-%d"))
            self.num_judges = event_data.get('num_judges', 3)
            self.timer_duration = event_data.get('timer_duration', 45)
            self.next_id = event_data.get('next_id', 1)
            
            # Load categories
            if 'categories' in event_data:
                self.category_manager.from_dict(event_data['categories'])
            
            # Load riders
            if 'riders' in event_data:
                for rider_data in event_data['riders']:
                    rider = Rider.from_dict(rider_data)
                    self.riders[rider.id] = rider
            
            return True
        except Exception as e:
            return False, str(e)
    
    def export_to_csv(self, filename):
        """Export competition results to CSV with categories separated"""
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write competition info
            writer.writerow([f"Competition: {self.competition_name}"])
            writer.writerow([f"Date: {self.competition_date}"])
            writer.writerow([])  # Empty row
            
            # Get categories with riders
            categories = self.get_categories_with_riders()
            
            # Write each category
            for category_name, riders in categories.items():
                # Sort riders by final score (descending)
                riders.sort(key=lambda r: r.final_score, reverse=True)
                
                # Category header
                writer.writerow([f"Category: {category_name}"])
                writer.writerow([])  # Empty row
                
                # Column headers
                headers = ['Position', 'Name', 'Age', 'Gender', 'Discipline']
                for i in range(self.num_judges):
                    headers.append(f'Run1 Judge{i+1}')
                headers.append('Run1 Average')
                for i in range(self.num_judges):
                    headers.append(f'Run2 Judge{i+1}')
                headers.append('Run2 Average')
                headers.append('Final Score')
                
                writer.writerow(headers)
                
                # Write rider data
                for position, rider in enumerate(riders, 1):
                    run1_avg = sum(rider.run1_scores) / len(rider.run1_scores) if rider.run1_scores else 0
                    run2_avg = sum(rider.run2_scores) / len(rider.run2_scores) if rider.run2_scores else 0
                    
                    row = [position, rider.name, rider.age, rider.gender, rider.discipline]
                    row.extend(rider.run1_scores)
                    row.append(f"{run1_avg:.1f}")
                    row.extend(rider.run2_scores)
                    row.append(f"{run2_avg:.1f}")
                    row.append(f"{rider.final_score:.1f}")
                    
                    writer.writerow(row)
                
                writer.writerow([])  # Empty row between categories
                writer.writerow([])  # Extra empty row
    
    def import_from_csv(self, filename):
        """Import riders from CSV"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    # Skip empty rows
                    if not row.get('Name', '').strip():
                        continue
                    
                    name = row.get('Name', '').strip()
                    age = int(row.get('Age', 0))
                    gender = row.get('Gender', 'Male').strip()
                    discipline = row.get('Discipline', '').strip()
                    category = row.get('Category', '').strip()
                    
                    if name and age > 0:
                        self.add_rider(name, age, gender, discipline, category)
            
            return True
        except Exception as e:
            return False, str(e)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.competition = CompetitionManager()
        self.current_filename = None  # Track current file
        self.is_modified = False  # Track if event has been modified
        self.setup_ui()
        self.setup_menu()
        self.selected_category = None  # Track selected category for results
        self.selected_discipline = None  # Track selected discipline for results
        self.update_title()
        
        # Initialize judges after UI is set up
        self.set_num_judges(3)
    
    def setup_ui(self):
        self.setWindowTitle("Freestyle Scooter Competition Judging System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.create_registration_tab()
        self.create_heats_tab()
        self.create_judging_tab()
        self.create_results_tab()
        
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_event_action = file_menu.addAction('New Event')
        new_event_action.triggered.connect(self.new_event)
        
        load_event_action = file_menu.addAction('Load Event')
        load_event_action.triggered.connect(self.load_event)
        
        save_event_action = file_menu.addAction('Save Event')
        save_event_action.triggered.connect(self.save_event)
        
        save_as_action = file_menu.addAction('Save Event As...')
        save_as_action.triggered.connect(self.save_event_as)
        
        file_menu.addSeparator()
        
        import_riders_action = file_menu.addAction('Import Riders from CSV')
        import_riders_action.triggered.connect(self.import_riders)
        
        export_results_action = file_menu.addAction('Export Results to CSV')
        export_results_action.triggered.connect(self.export_results)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # Options menu
        options_menu = menubar.addMenu('Options')
        
        manage_categories_action = options_menu.addAction('Manage Categories')
        manage_categories_action.triggered.connect(self.manage_categories)
        
        set_judges_action = options_menu.addAction('Set Number of Judges')
        set_judges_action.triggered.connect(self.set_judges_dialog)
        
        set_timer_action = options_menu.addAction('Set Timer Duration')
        set_timer_action.triggered.connect(self.set_timer_duration)
        
        set_event_name_action = options_menu.addAction('Set Event Name')
        set_event_name_action.triggered.connect(self.set_event_name)
    
    def update_title(self):
        """Update window title with current filename and modified status"""
        title = "Freestyle Scooter Competition Judging System"
        if self.current_filename:
            filename = Path(self.current_filename).name
            title += f" - {filename}"
        if self.is_modified:
            title += " *"
        self.setWindowTitle(title)
    
    def set_modified(self, modified=True):
        """Set the modified status and update title"""
        self.is_modified = modified
        self.update_title()
    
    def check_save_changes(self):
        """Check if there are unsaved changes and prompt user"""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save the current event?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                return self.save_event()
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        return True
    
    def new_event(self):
        """Create a new event"""
        if not self.check_save_changes():
            return
        
        # Clear all data
        self.competition.clear_all()
        self.current_filename = None
        self.set_modified(False)
        
        # Refresh all views
        self.refresh_riders_table()
        self.refresh_category_combos()
        self.refresh_heats()
        self.refresh_results()
        
        QMessageBox.information(self, "New Event", "New event created successfully!")
    
    def load_event(self):
        """Load an event from file"""
        if not self.check_save_changes():
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Event", "", "Event Files (*.json)"
        )
        
        if filename:
            result = self.competition.load_event(filename)
            if result is True:
                self.current_filename = filename
                self.set_modified(False)
                
                # Update timer duration
                self.time_remaining = self.competition.timer_duration
                self.timer_label.setText(str(self.time_remaining))
                
                # Update number of judges
                self.set_num_judges(self.competition.num_judges)
                
                # Refresh all views
                self.refresh_riders_table()
                self.refresh_category_combos()
                self.refresh_heats()
                self.refresh_results()
                
                QMessageBox.information(
                    self, "Load Successful",
                    "Event loaded successfully!"
                )
            else:
                QMessageBox.warning(
                    self, "Load Error",
                    f"Error loading event: {result[1] if isinstance(result, tuple) else 'Unknown error'}"
                )
    
    def save_event(self):
        """Save the current event"""
        if self.current_filename:
            result = self.competition.save_event(self.current_filename)
            if result is True:
                self.set_modified(False)
                QMessageBox.information(
                    self, "Save Successful",
                    "Event saved successfully!"
                )
                return True
            else:
                QMessageBox.warning(
                    self, "Save Error",
                    f"Error saving event: {result[1] if isinstance(result, tuple) else 'Unknown error'}"
                )
                return False
        else:
            return self.save_event_as()
    
    def save_event_as(self):
        """Save the event with a new filename"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Event As", 
            f"{self.competition.competition_name.replace(' ', '_')}_{self.competition.competition_date}.json",
            "Event Files (*.json)"
        )
        
        if filename:
            # Update timer duration from current state
            self.competition.timer_duration = self.time_remaining
            
            result = self.competition.save_event(filename)
            if result is True:
                self.current_filename = filename
                self.set_modified(False)
                QMessageBox.information(
                    self, "Save Successful",
                    "Event saved successfully!"
                )
                return True
            else:
                QMessageBox.warning(
                    self, "Save Error",
                    f"Error saving event: {result[1] if isinstance(result, tuple) else 'Unknown error'}"
                )
                return False
        return False
    
    def set_event_name(self):
        """Set the event name"""
        text, ok = QInputDialog.getText(
            self,
            "Set Event Name",
            "Enter event name:",
            text=self.competition.competition_name
        )
        if ok and text:
            self.competition.competition_name = text
            self.set_modified(True)
    
    def set_judges_dialog(self):
        """Set number of judges dialog"""
        num, ok = QInputDialog.getInt(
            self,
            "Set Number of Judges",
            "Enter number of judges:",
            value=self.competition.num_judges,
            minValue=1,
            maxValue=10
        )
        if ok:
            self.set_num_judges(num)
            self.set_modified(True)
    
    def set_num_judges(self, num_judges):
        """Set the number of judges and update UI"""
        self.competition.num_judges = num_judges
        
        # Update all rider scores to match new judge count
        for rider in self.competition.riders.values():
            # Adjust run1_scores
            if len(rider.run1_scores) < num_judges:
                rider.run1_scores.extend([0.0] * (num_judges - len(rider.run1_scores)))
            elif len(rider.run1_scores) > num_judges:
                rider.run1_scores = rider.run1_scores[:num_judges]
            
            # Adjust run2_scores
            if len(rider.run2_scores) < num_judges:
                rider.run2_scores.extend([0.0] * (num_judges - len(rider.run2_scores)))
            elif len(rider.run2_scores) > num_judges:
                rider.run2_scores = rider.run2_scores[:num_judges]
            
            rider.calculate_final_score()
        
        # Rebuild judge widgets
        self.rebuild_judge_widgets()
        
        # Update results table columns
        self.setup_results_table()
        self.refresh_results()
    
    def rebuild_judge_widgets(self):
        """Rebuild judge scoring widgets based on current number of judges"""
        # Clear existing judge widgets
        for widget in self.judge_widgets:
            widget.deleteLater()
        self.judge_widgets.clear()
        
        # Clear layout
        for i in reversed(range(self.judges_layout.count())):
            self.judges_layout.itemAt(i).widget().deleteLater()
        
        # Create new judge widgets
        for i in range(self.competition.num_judges):
            judge_widget = JudgeScoreWidget(i)
            judge_widget.score_updated.connect(self.update_judge_score)
            self.judge_widgets.append(judge_widget)
            self.judges_layout.addWidget(judge_widget)
        
        # Add stretch at the end
        self.judges_layout.addStretch()
    
    def set_timer_duration(self):
        """Prompt user to set new timer duration in seconds"""
        text, ok = QInputDialog.getInt(
            self,
            "Set Timer Duration",
            "Enter new timer duration (seconds):",
            value=self.time_remaining,
            minValue=10,
            maxValue=300
        )
        if ok:
            self.time_remaining = text
            self.competition.timer_duration = text
            self.timer_label.setText(str(self.time_remaining))
            self.set_modified(True)
    
    def manage_categories(self):
        """Open the Manage Categories dialog"""
        dialog = CategoryDialog(self.competition.category_manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_category_combos()
            self.set_modified(True)
    
    def create_registration_tab(self):
        """Create rider registration tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Rider")
        edit_btn = QPushButton("Edit Rider")
        remove_btn = QPushButton("Remove Rider")
        
        add_btn.clicked.connect(self.add_rider)
        edit_btn.clicked.connect(self.edit_rider)
        remove_btn.clicked.connect(self.remove_rider)
        
        controls_layout.addWidget(add_btn)
        controls_layout.addWidget(edit_btn)
        controls_layout.addWidget(remove_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Riders table
        self.riders_table = QTableWidget()
        self.riders_table.setColumnCount(6)
        self.riders_table.setHorizontalHeaderLabels([
            "ID", "Name", "Age", "Gender", "Discipline", "Category"
        ])
        self.riders_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.riders_table)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Registration")
    
    def create_heats_tab(self):
        """Create heats overview tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Discipline filter
        discipline_label = QLabel("Filter by Discipline:")
        self.heats_discipline_combo = QComboBox()
        self.heats_discipline_combo.addItem("All Disciplines")
        self.heats_discipline_combo.currentTextChanged.connect(self.filter_heats_by_discipline)
        
        refresh_btn = QPushButton("Refresh Categories")
        refresh_btn.clicked.connect(self.refresh_heats)
        
        controls_layout.addWidget(discipline_label)
        controls_layout.addWidget(self.heats_discipline_combo)
        controls_layout.addWidget(refresh_btn)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Scroll area for heats
        scroll = QScrollArea()
        self.heats_widget = QWidget()
        self.heats_layout = QVBoxLayout()
        self.heats_widget.setLayout(self.heats_layout)
        scroll.setWidget(self.heats_widget)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Categories")
    
    def create_judging_tab(self):
        """Create judging interface tab"""
        tab = QWidget()
        main_layout = QHBoxLayout()
        
        # Left side - Rider selection
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout()
        
        # Category selection
        category_layout = QVBoxLayout()
        category_layout.addWidget(QLabel("Select Category:"))
        self.category_combo = QComboBox()
        self.category_combo.currentTextChanged.connect(self.load_judging_category)
        category_layout.addWidget(self.category_combo)
        left_layout.addLayout(category_layout)
        
        # Rider list
        left_layout.addWidget(QLabel("Riders in Category:"))
        self.riders_list = QTableWidget()
        self.riders_list.setColumnCount(2)
        self.riders_list.setHorizontalHeaderLabels(["Name", "Age"])
        self.riders_list.horizontalHeader().setStretchLastSection(True)
        self.riders_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.riders_list.itemSelectionChanged.connect(self.on_rider_selected)
        left_layout.addWidget(self.riders_list)
        
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel)
        
        # Right side - Judging interface
        self.judging_right_panel = QWidget()
        self.build_judging_right_panel()
        main_layout.addWidget(self.judging_right_panel)
        
        tab.setLayout(main_layout)
        self.tab_widget.addTab(tab, "Judging")
        
        # Initialize timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.time_remaining = 45
        self.current_run = 1
        self.current_rider_id = None
    
    def build_judging_right_panel(self):
        """Build the right panel of judging interface"""
        right_layout = QVBoxLayout()
        
        # Current rider info
        self.current_rider_label = QLabel("No rider selected")
        self.current_rider_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.current_rider_label.setFont(font)
        right_layout.addWidget(self.current_rider_label)
        
        # Timer section
        timer_group = QGroupBox("Timer")
        timer_layout = QVBoxLayout()
        
        self.timer_label = QLabel("45")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_font = QFont()
        timer_font.setPointSize(48)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)
        self.timer_label.setStyleSheet("color: green; border: 2px solid black; padding: 20px;")
        timer_layout.addWidget(self.timer_label)
        
        # Timer controls
        timer_controls = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.reset_btn = QPushButton("Reset")
        
        self.start_btn.clicked.connect(self.start_timer)
        self.pause_btn.clicked.connect(self.pause_timer)
        self.reset_btn.clicked.connect(self.reset_timer)
        
        for btn in [self.start_btn, self.pause_btn, self.reset_btn]:
            btn.setMinimumHeight(40)
        
        timer_controls.addWidget(self.start_btn)
        timer_controls.addWidget(self.pause_btn)
        timer_controls.addWidget(self.reset_btn)
        timer_layout.addLayout(timer_controls)
        
        timer_group.setLayout(timer_layout)
        right_layout.addWidget(timer_group)
        
        # Run selection
        run_group = QGroupBox("Select Run")
        run_layout = QHBoxLayout()
        
        # Create radio buttons for run selection
        self.run1_btn = QRadioButton("Run 1")
        self.run2_btn = QRadioButton("Run 2")
        self.run1_btn.setChecked(True)  # Default to Run 1
        
        self.run1_btn.clicked.connect(lambda: self.select_run(1))
        self.run2_btn.clicked.connect(lambda: self.select_run(2))
        
        for btn in [self.run1_btn, self.run2_btn]:
            btn.setMinimumHeight(40)
        
        run_layout.addWidget(self.run1_btn)
        run_layout.addWidget(self.run2_btn)
        run_group.setLayout(run_layout)
        right_layout.addWidget(run_group)
        
        # Judges scoring section
        judges_group = QGroupBox("Judges Scoring")
        self.judges_layout = QHBoxLayout()
        
        self.judge_widgets = []
        
        judges_group.setLayout(self.judges_layout)
        right_layout.addWidget(judges_group)
        
        # Current scores display
        scores_group = QGroupBox("Current Scores")
        scores_layout = QVBoxLayout()
        
        self.scores_display = QLabel("No scores entered")
        self.scores_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scores_layout.addWidget(self.scores_display)
        
        scores_group.setLayout(scores_layout)
        right_layout.addWidget(scores_group)
        
        right_layout.addStretch()
        self.judging_right_panel.setLayout(right_layout)
    
    def create_results_tab(self):
        """Create results tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Category filter
        filter_label = QLabel("Filter by Category:")
        self.results_category_combo = QComboBox()
        self.results_category_combo.addItem("All Categories")
        self.results_category_combo.currentTextChanged.connect(self.filter_results_by_category)
        
        # Discipline filter  
        discipline_filter_label = QLabel("Filter by Discipline:")
        self.results_discipline_combo = QComboBox()
        self.results_discipline_combo.addItem("All Disciplines")
        self.results_discipline_combo.currentTextChanged.connect(self.filter_results_by_discipline)
        
        refresh_results_btn = QPushButton("Refresh Results")
        refresh_results_btn.clicked.connect(self.refresh_results)
        
        controls_layout.addWidget(discipline_filter_label)
        controls_layout.addWidget(self.results_discipline_combo)
        controls_layout.addWidget(filter_label)
        controls_layout.addWidget(self.results_category_combo)
        controls_layout.addWidget(refresh_results_btn)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.setup_results_table()
        layout.addWidget(self.results_table)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Results")
    
    def setup_results_table(self):
        """Setup results table columns based on number of judges"""
        columns = ["Position", "Name", "Discipline", "Category", "Run 1 Avg", "Run 2 Avg", "Best Score", "Age"]
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        self.results_table.horizontalHeader().setStretchLastSection(True)
    
    def add_rider(self):
        """Add a new rider"""
        dialog = RiderDialog(self.competition.category_manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_rider_data()
            if data['name'].strip():
                self.competition.add_rider(
                    data['name'], data['age'], data['gender'], data['discipline'], data['category']
                )
                self.refresh_riders_table()
                self.refresh_category_combos()
                self.set_modified(True)
    
    def edit_rider(self):
        """Edit selected rider"""
        current_row = self.riders_table.currentRow()
        if current_row >= 0:
            rider_id = int(self.riders_table.item(current_row, 0).text())
            rider = self.competition.riders.get(rider_id)
            
            if rider:
                dialog = RiderDialog(self.competition.category_manager, rider, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    data = dialog.get_rider_data()
                    self.competition.update_rider(rider_id, **data)
                    self.refresh_riders_table()
                    self.refresh_category_combos()
                    self.set_modified(True)
    
    def remove_rider(self):
        """Remove selected rider"""
        current_row = self.riders_table.currentRow()
        if current_row >= 0:
            rider_id = int(self.riders_table.item(current_row, 0).text())
            reply = QMessageBox.question(
                self, "Confirm Removal",
                "Are you sure you want to remove this rider?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.competition.remove_rider(rider_id)
                self.refresh_riders_table()
                self.refresh_category_combos()
                self.set_modified(True)
    
    def refresh_riders_table(self):
        """Refresh the riders table"""
        riders = list(self.competition.riders.values())
        self.riders_table.setRowCount(len(riders))
        
        for row, rider in enumerate(riders):
            self.riders_table.setItem(row, 0, QTableWidgetItem(str(rider.id)))
            self.riders_table.setItem(row, 1, QTableWidgetItem(rider.name))
            self.riders_table.setItem(row, 2, QTableWidgetItem(str(rider.age)))
            self.riders_table.setItem(row, 3, QTableWidgetItem(rider.gender))
            self.riders_table.setItem(row, 4, QTableWidgetItem(rider.discipline))
            self.riders_table.setItem(row, 5, QTableWidgetItem(rider.category))
    
    def refresh_heats(self):
        """Refresh heats/categories display"""
        # Clear existing layout
        for i in reversed(range(self.heats_layout.count())):
            child = self.heats_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Update discipline filter combo
        disciplines = list(self.competition.get_disciplines_with_riders().keys())
        current_discipline_filter = self.heats_discipline_combo.currentText()
        self.heats_discipline_combo.clear()
        self.heats_discipline_combo.addItem("All Disciplines")
        self.heats_discipline_combo.addItems(disciplines)
        
        if current_discipline_filter in ["All Disciplines"] + disciplines:
            self.heats_discipline_combo.setCurrentText(current_discipline_filter)
        
        # Display categories
        categories = self.competition.get_categories_with_riders()
        
        for category_name, riders in categories.items():
            # Create category group
            group = QGroupBox(f"{category_name} ({len(riders)} riders)")
            group_layout = QVBoxLayout()
            
            for i, rider in enumerate(riders, 1):
                rider_label = QLabel(f"{i}. {rider.name} ({rider.age}y, {rider.gender})")
                group_layout.addWidget(rider_label)
            
            group.setLayout(group_layout)
            self.heats_layout.addWidget(group)
        
        self.heats_layout.addStretch()
    
    def filter_heats_by_discipline(self, discipline_filter):
        """Filter heats display by discipline"""
        # Clear existing layout
        for i in reversed(range(self.heats_layout.count())):
            child = self.heats_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        categories = self.competition.get_categories_with_riders()
        
        for category_name, riders in categories.items():
            # Check if we should show this category based on discipline filter
            if discipline_filter != "All Disciplines":
                if not category_name.startswith(discipline_filter):
                    continue
            
            # Create category group
            group = QGroupBox(f"{category_name} ({len(riders)} riders)")
            group_layout = QVBoxLayout()
            
            for i, rider in enumerate(riders, 1):
                rider_label = QLabel(f"{i}. {rider.name} ({rider.age}y, {rider.gender})")
                group_layout.addWidget(rider_label)
            
            group.setLayout(group_layout)
            self.heats_layout.addWidget(group)
        
        self.heats_layout.addStretch()
    
    def refresh_category_combos(self):
        """Refresh category combo boxes"""
        categories = list(self.competition.get_categories_with_riders().keys())
        disciplines = list(self.competition.get_disciplines_with_riders().keys())
        
        # Update judging category combo
        current_category = self.category_combo.currentText()
        self.category_combo.clear()
        self.category_combo.addItems(categories)
        
        if current_category in categories:
            self.category_combo.setCurrentText(current_category)
        
        # Update results filter combos
        self.results_category_combo.clear()
        self.results_category_combo.addItem("All Categories")
        self.results_category_combo.addItems(categories)
        
        self.results_discipline_combo.clear()
        self.results_discipline_combo.addItem("All Disciplines")
        self.results_discipline_combo.addItems(disciplines)
    
    def load_judging_category(self, category_name):
        """Load riders for selected category"""
        if not category_name:
            self.riders_list.setRowCount(0)
            return
        
        categories = self.competition.get_categories_with_riders()
        if category_name in categories:
            riders = categories[category_name]
            self.riders_list.setRowCount(len(riders))
            
            for row, rider in enumerate(riders):
                self.riders_list.setItem(row, 0, QTableWidgetItem(rider.name))
                self.riders_list.setItem(row, 1, QTableWidgetItem(str(rider.age)))
                
                # Store rider ID in the first column item
                self.riders_list.item(row, 0).setData(Qt.ItemDataRole.UserRole, rider.id)
    
    def on_rider_selected(self):
        """Handle rider selection from the list"""
        current_row = self.riders_list.currentRow()
        if current_row >= 0:
            rider_id = self.riders_list.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            rider = self.competition.riders.get(rider_id)
            
            if rider:
                self.current_rider_id = rider_id
                self.current_rider_label.setText(f"Current Rider: {rider.name}")
                
                # Update judge widgets with current rider
                for judge_widget in self.judge_widgets:
                    judge_widget.set_rider(rider_id)
                
                # Load current scores for the selected run
                self.load_current_scores()
    
    def select_run(self, run_number):
        """Select which run to judge"""
        self.current_run = run_number
        
        # Update button states
        self.run1_btn.setChecked(run_number == 1)
        self.run2_btn.setChecked(run_number == 2)
        
        # Load scores for the selected run
        self.load_current_scores()
    
    def load_current_scores(self):
        """Load current scores for the selected rider and run"""
        if self.current_rider_id is None:
            return
        
        rider = self.competition.riders.get(self.current_rider_id)
        if not rider:
            return
        
        # Get scores for current run
        if self.current_run == 1:
            scores = rider.run1_scores
        else:
            scores = rider.run2_scores
        
        # Update judge score widgets
        for i, judge_widget in enumerate(self.judge_widgets):
            if i < len(scores):
                judge_widget.set_score(scores[i])
            else:
                judge_widget.set_score(0.0)
        
        # Update scores display
        self.update_scores_display()
    
    def update_judge_score(self, rider_id, judge_number, score):
        """Update judge score"""
        if rider_id == self.current_rider_id:
            self.competition.update_score(rider_id, self.current_run, judge_number, score)
            self.update_scores_display()
            self.set_modified(True)
    
    def update_scores_display(self):
        """Update the scores display"""
        if self.current_rider_id is None:
            self.scores_display.setText("No rider selected")
            return
        
        rider = self.competition.riders.get(self.current_rider_id)
        if not rider:
            return
        
        # Get current run scores
        if self.current_run == 1:
            scores = rider.run1_scores
            run_text = "Run 1"
        else:
            scores = rider.run2_scores
            run_text = "Run 2"
        
        # Calculate average
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Format display text
        scores_text = f"{run_text} Scores:\n"
        for i, score in enumerate(scores):
            scores_text += f"Judge {i+1}: {score:.1f}\n"
        scores_text += f"Average: {avg_score:.1f}"
        
        self.scores_display.setText(scores_text)
    
    def start_timer(self):
        """Start the timer"""
        self.timer.start(1000)  # Update every second
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
    
    def pause_timer(self):
        """Pause the timer"""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def reset_timer(self):
        """Reset the timer"""
        self.timer.stop()
        self.time_remaining = self.competition.timer_duration
        self.timer_label.setText(str(self.time_remaining))
        self.timer_label.setStyleSheet("color: green; border: 2px solid black; padding: 20px;")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def update_timer(self):
        """Update timer display"""
        self.time_remaining -= 1
        self.timer_label.setText(str(self.time_remaining))
        
        # Change color based on time remaining
        if self.time_remaining <= 10:
            self.timer_label.setStyleSheet("color: red; border: 2px solid red; padding: 20px;")
        elif self.time_remaining <= 20:
            self.timer_label.setStyleSheet("color: orange; border: 2px solid orange; padding: 20px;")
        
        if self.time_remaining <= 0:
            self.timer.stop()
            self.timer_label.setText("TIME!")
            self.timer_label.setStyleSheet("color: red; border: 3px solid red; padding: 20px; background-color: yellow;")
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
    
    def filter_results_by_category(self, category_filter):
        """Filter results by selected category"""
        self.selected_category = category_filter if category_filter != "All Categories" else None
        self.refresh_results()
    
    def filter_results_by_discipline(self, discipline_filter):
        """Filter results by selected discipline"""
        self.selected_discipline = discipline_filter if discipline_filter != "All Disciplines" else None
        self.refresh_results()
    
    def refresh_results(self):
        """Refresh results table"""
        # Get all categories with riders
        categories = self.competition.get_categories_with_riders()
        
        results = []
        
        # Apply filters
        for category_name, category_riders in categories.items():
            # Check discipline filter
            if self.selected_discipline and self.selected_discipline != "All Disciplines":
                if not category_name.startswith(self.selected_discipline):
                    continue
            
            # Check category filter
            if self.selected_category and self.selected_category != "All Categories":
                if category_name != self.selected_category:
                    continue
            
            # Sort riders in each category by final score (descending)
            category_riders.sort(key=lambda r: r.final_score, reverse=True)
            
            for position, rider in enumerate(category_riders, 1):
                run1_avg = sum(rider.run1_scores) / len(rider.run1_scores) if rider.run1_scores else 0
                run2_avg = sum(rider.run2_scores) / len(rider.run2_scores) if rider.run2_scores else 0
                
                results.append({
                    'position': position,
                    'name': rider.name,
                    'discipline': rider.discipline,
                    'category': rider.category,
                    'run1_avg': run1_avg,
                    'run2_avg': run2_avg,
                    'best_score': rider.final_score,
                    'age': rider.age
                })
        
        # Update table
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result['position'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(result['name']))
            self.results_table.setItem(row, 2, QTableWidgetItem(result['discipline']))
            self.results_table.setItem(row, 3, QTableWidgetItem(result['category']))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{result['run1_avg']:.1f}"))
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{result['run2_avg']:.1f}"))
            self.results_table.setItem(row, 6, QTableWidgetItem(f"{result['best_score']:.1f}"))
            self.results_table.setItem(row, 7, QTableWidgetItem(str(result['age'])))
    
    def import_riders(self):
        """Import riders from CSV file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Riders", "", "CSV Files (*.csv)"
        )
        
        if filename:
            result = self.competition.import_from_csv(filename)
            if result is True:
                QMessageBox.information(
                    self, "Import Successful",
                    "Riders imported successfully!"
                )
                self.refresh_riders_table()
                self.refresh_category_combos()
                self.set_modified(True)
            else:
                QMessageBox.warning(
                    self, "Import Error",
                    f"Error importing riders: {result[1] if isinstance(result, tuple) else 'Unknown error'}"
                )
    
    def export_results(self):
        """Export results to CSV file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Results", 
            f"competition_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                self.competition.export_to_csv(filename)
                QMessageBox.information(
                    self, "Export Successful",
                    "Results exported successfully!"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Export Error",
                    f"Error exporting results: {str(e)}"
                )
    
    def closeEvent(self, event):
        """Handle window close event"""
        if not self.check_save_changes():
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()