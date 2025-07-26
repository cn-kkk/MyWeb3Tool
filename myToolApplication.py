import markdown
import sys
import os
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTextEdit, QPushButton, QLabel, QPlainTextEdit, QFormLayout, QLineEdit, 
    QStackedWidget, QSizePolicy, QSpacerItem, QComboBox, QMessageBox,
    QFrame, QSplitter, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QStyledItemDelegate, QProxyStyle, QStyle
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QIcon

# 导入后端控制器和日志工具
from applicationController import app_controller
from util.log_util import log_util

from config import APP_NAME, APP_VERSION, UI_FONTS, LOGS_DIR, LOG_FILENAME_PREFIX, LOG_FILENAME_FORMAT, API_URL_VALID_PREFIXES

class BackendInitializationThread(QThread):
    """用于在后台初始化控制器的线程"""
    initialization_done = pyqtSignal(bool, str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        try:
            self.controller.initialize_app()
            self.initialization_done.emit(True, "Backend initialized successfully.")
        except Exception as e:
            log_util.error("Backend", f"Backend initialization failed: {e}", exc_info=True)
            self.initialization_done.emit(False, str(e))

def resource_path(relative_path):
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        print(f"resource_path error for {relative_path}: {e}")
        return relative_path

class LogWidget(QTextEdit):
    """日志显示组件，只负责显示从回调函数传递过来的日志。"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont('Consolas', 10))
        pal = self.palette()
        pal.setColor(QPalette.Base, QColor(245, 245, 245))
        pal.setColor(QPalette.Text, QColor(30, 30, 30))
        self.setPalette(pal)
        self.setFixedHeight(200)
    
    def append_log(self, msg):
        self.append(msg)
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

class StyledSidebar(QListWidget):
    """样式化的侧边栏"""
    def __init__(self, items, width=200):
        super().__init__()
        self.setFixedWidth(width)
        self.setSpacing(8)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet('''
            QListView, QListWidget { outline: none; }
            QListWidget { border: none; background: transparent; }
            QListWidget::item { background: #f0f0f0; border: 1px solid #d0d0d0; border-radius: 8px; margin: 4px 0; padding: 12px 16px; font-size: 14px; color: #333; font-weight: 500; }
            QListWidget::item:hover { background: #e0e0e0; border-color: #b0b0b0; }
            QListWidget::item:selected { background: #0078d4; color: white; border-color: #0078d4; }
        ''')
        for item_text in items:
            self.addItem(item_text)
        if self.count() > 0:
            self.setCurrentRow(0)

class NoFocusRectStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect: return
        super().drawPrimitive(element, option, painter, widget)

class EditModeDelegate(QStyledItemDelegate):
    def __init__(self, parent, is_editing_func):
        super().__init__(parent)
        self.is_editing_func = is_editing_func
    def paint(self, painter, option, index):
        if self.is_editing_func() and bool(index.flags() & Qt.ItemFlag.ItemIsEditable):
            painter.save()
            painter.fillRect(option.rect, QColor('#fffbe6'))
            painter.restore()
        super().paint(painter, option, index)

class ConfigTableWidget(QTableWidget):
    """配置表格组件"""
    header_key_map = { "ID": "id", "IP地址": "ip", "端口": "port", "用户名": "username", "密码": "password", "私钥": "privateKey", "地址": "address" }
    def __init__(self, headers, data=None):
        super().__init__()
        self.headers = headers
        self._editing = False
        self.setItemDelegate(EditModeDelegate(self, lambda: self._editing))
        self.setStyle(NoFocusRectStyle(self.style()))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setStyleSheet('''
            QTableWidget { background-color: white; border: 1px solid #d0d0d0; border-radius: 12px; gridline-color: #e0e0e0; }
            QTableWidget::item { padding: 8px; border: none; border-radius: 8px; background: transparent; }
            QTableWidget::item:selected { background: transparent; border: 2px solid orange; color: #333; }
            QTableWidget::item:focus { outline: none; }
            QHeaderView::section { background-color: #f8f9fa; padding: 8px; border: none; border-bottom: 1px solid #d0d0d0; font-weight: bold; font-size: 15px; }
        ''')
        for i, h in enumerate(headers):
            if h == "ID":
                self.setColumnWidth(i, 60)
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            else:
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(True)
        if data: self.load_data(data)
    
    def load_data(self, data):
        self.setRowCount(len(data))
        for row, item in enumerate(data):
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                if key in item:
                    value = str(item[key])
                    table_item = QTableWidgetItem(value)
                    table_item.setFlags(Qt.ItemFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable))
                    self.setItem(row, col, table_item)
    
    def get_data(self):
        data = []
        for row in range(self.rowCount()):
            row_data = {}
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                item = self.item(row, col)
                if item: row_data[key] = item.text()
            if row_data: data.append(row_data)
        return data
    
    def set_editable(self, editable):
        self._editing = editable
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    flags = item.flags()
                    if editable:
                        item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(QColor('#fffbe6'))
                        font = item.font(); font.setBold(True); item.setFont(font)
                    else:
                        item.setFlags(Qt.ItemFlags(flags & ~Qt.ItemFlag.ItemIsEditable))
                        item.setBackground(QColor('white'))
                        font = item.font(); font.setBold(False); item.setFont(font)
        self.viewport().update()

class IPConfigWidget(QWidget):
    """IP配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("IP配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        headers = ["ID", "IP地址", "端口", "用户名", "密码"]; self.table = ConfigTableWidget(headers); layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        proxies = app_controller.get_ip_configs()
        configs = [{"id": i, "ip": p.ip, "port": str(p.port), "username": p.username, "password": p.password} for i, p in enumerate(proxies, 1)]
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入IP配置编辑模式")
        else:
            self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消IP配置编辑")
    
    def save_config(self):
        data = self.table.get_data()
        configs = [{"ip": item["ip"], "port": item["port"], "username": item["username"], "password": item["password"]} for item in data]
        if app_controller.save_ip_configs(configs):
            self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config(); QMessageBox.information(self, "成功", "IP配置保存成功")
        else: QMessageBox.critical(self, "错误", "IP配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config()

class WalletConfigWidget(QWidget):
    """钱包配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("钱包配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        headers = ["ID", "私钥", "地址"]; self.table = ConfigTableWidget(headers); layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        wallets = app_controller.get_wallet_configs()
        configs = [{"id": i, "privateKey": w.private_key, "address": w.address} for i, w in enumerate(wallets, 1)]
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入钱包配置编辑模式")
        else:
            self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消钱包配置编辑")
    
    def save_config(self):
        data = self.table.get_data()
        configs = [{"privateKey": item["privateKey"], "address": item["address"]} for item in data]
        if app_controller.save_wallet_configs(configs):
            self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config(); QMessageBox.information(self, "成功", "钱包配置保存成功")
        else: QMessageBox.critical(self, "错误", "钱包配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config()

class BrowserConfigWidget(QWidget):
    """浏览器ID配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("浏览器ID配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        desc_label = QLabel("第一行：API地址，第二行及以后：浏览器ID（每行一个）"); desc_label.setFont(QFont('Microsoft YaHei', 12)); desc_label.setStyleSheet("color: #666; margin: 10px 0;"); layout.addWidget(desc_label)
        self.text_edit = QPlainTextEdit(); self.text_edit.setFont(QFont('Consolas', 11)); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.text_edit.setReadOnly(True); layout.addWidget(self.text_edit)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        content = app_controller.get_browser_configs()
        self.text_edit.setPlainText(content)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        if self.is_editing:
            self.text_edit.setReadOnly(False); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: #fffbe6; border: 2px solid #107c10; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #107c10; } '''); self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入浏览器ID配置编辑模式")
        else:
            self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消浏览器ID配置编辑")
    
    def save_config(self):
        content = self.text_edit.toPlainText()
        if app_controller.save_browser_configs(content):
            log_util.info("UI", f"浏览器配置保存成功"); QMessageBox.information(self, "成功", "浏览器配置保存成功"); self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.load_config()
        else: QMessageBox.critical(self, "错误", "浏览器配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.load_config()

class HomeTab(QWidget):
    """首页标签页"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_readme()
        
    def init_ui(self):
        layout = QVBoxLayout(); self.readme_display = QTextEdit(); self.readme_display.setReadOnly(True); layout.addWidget(self.readme_display); self.setLayout(layout)

    def load_readme(self):
        try:
            readme_path = resource_path('README.md')
            with open(readme_path, 'r', encoding='utf-8') as f: md_text = f.read()
            css = """<style> body { font-family: 'Microsoft YaHei'; font-size: 16px; line-height: 1.6; } h1 { font-size: 28px; color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 10px; } h2 { font-size: 24px; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 20px;} h3 { font-size: 20px; } code { font-family: 'Consolas', 'Courier New', monospace; background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; } pre { background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 10px; white-space: pre-wrap; word-wrap: break-word; } pre > code { background-color: transparent; padding: 0; } ul, ol { padding-left: 20px; } </style>"""
            html = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
            self.readme_display.setHtml(css + html)
            log_util.info("UI", "README.md 已加载到首页。")
        except Exception as e:
            log_util.error("UI", f"加载 README.md 失败: {e}")
            self.readme_display.setText(f"加载 README.md 失败: {e}")

class ConfigTab(QWidget):
    """配置标签页"""
    def __init__(self):
        super().__init__()
        self._last_sidebar_index = 0
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        sidebar_items = ["IP配置", "钱包配置", "浏览器ID配置"]; self.sidebar = StyledSidebar(sidebar_items, 200); self.sidebar.currentRowChanged.connect(self.on_sidebar_changed); layout.addWidget(self.sidebar)
        self.content_stack = QStackedWidget()
        self.ip_config_widget = IPConfigWidget(); self.content_stack.addWidget(self.ip_config_widget)
        self.wallet_config_widget = WalletConfigWidget(); self.content_stack.addWidget(self.wallet_config_widget)
        self.browser_config_widget = BrowserConfigWidget(); self.content_stack.addWidget(self.browser_config_widget)
        layout.addWidget(self.content_stack); self.setLayout(layout)
        
    def on_sidebar_changed(self, index):
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'is_editing') and current_widget.is_editing: current_widget.exit_edit_mode()
        self._last_sidebar_index = index; self.content_stack.setCurrentIndex(index)
        items = ["IP配置", "钱包配置", "浏览器ID配置"]
        if 0 <= index < len(items):
            if index == 0: self.ip_config_widget.load_config()
            elif index == 1: self.wallet_config_widget.load_config()
            elif index == 2: self.browser_config_widget.load_config()

class ProjectTab(QWidget):
    """项目标签页，自动加载myProject下所有项目脚本"""
    def __init__(self):
        super().__init__()
        self.project_classes = []
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(); self.sidebar = StyledSidebar([], 200); self.sidebar.currentRowChanged.connect(self.on_sidebar_changed); layout.addWidget(self.sidebar)
        splitter = QFrame(); splitter.setFrameShape(QFrame.VLine); splitter.setFrameShadow(QFrame.Sunken); splitter.setLineWidth(2); layout.addWidget(splitter)
        self.content_stack = QStackedWidget(); layout.addWidget(self.content_stack); self.setLayout(layout)

    def populate_projects(self, projects):
        self.project_classes = projects
        self.sidebar.clear()
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0); self.content_stack.removeWidget(widget); widget.deleteLater()
        for proj in self.project_classes:
            self.sidebar.addItem(proj['project_name']); self.content_stack.addWidget(self.create_project_widget(proj))
        if self.project_classes: self.sidebar.setCurrentRow(0)

    def create_project_widget(self, proj):
        widget = QWidget(); vlayout = QVBoxLayout()
        project_desc_label = QLabel(proj.get('project_desc', '没有项目描述。')); project_desc_label.setFont(QFont('Microsoft YaHei', 12)); project_desc_label.setStyleSheet('color: #666; margin: 10px 0;'); vlayout.addWidget(project_desc_label)
        run_all_btn = QPushButton(f"一键运行 {proj['project_name']} 所有任务"); run_all_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; font-weight: bold; font-size: 16px; padding: 12px; border-radius: 8px; } QPushButton:hover { background-color: #106ebe; } '''); run_all_btn.clicked.connect(lambda _, p=proj: [app_controller.dispatch_task(p['project_name'], task['name']) for task in p['tasks']]); vlayout.addWidget(run_all_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); vlayout.addWidget(line)
        for task in proj['tasks']:
            task_group_layout = QHBoxLayout(); task_label = QLabel(f"<b>{task['name']}</b>: {task['desc']}"); task_label.setWordWrap(True)
            task_btn = QPushButton(f"运行"); task_btn.setFixedWidth(120); task_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; font-weight: bold; font-size: 16px; padding: 12px; border-radius: 5px; } QPushButton:hover { background-color: #0e6e0e; } '''); task_btn.clicked.connect(lambda _, p=proj, t=task: app_controller.dispatch_task(p['project_name'], t['name']))
            task_group_layout.addWidget(task_label); task_group_layout.addStretch(); task_group_layout.addWidget(task_btn); vlayout.addLayout(task_group_layout)
        vlayout.addStretch(); widget.setLayout(vlayout); return widget

    def on_sidebar_changed(self, index): self.content_stack.setCurrentIndex(index)

class MyToolApplication(QWidget):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.controller = app_controller
        self.init_ui()
        self.start_backend_initialization()
        
    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}"); self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(''' QWidget { background-color: white; font-family: 'Microsoft YaHei'; } QTabWidget::pane { border: none; background: white; } QTabBar::tab { background: #f0f0f0; color: #333; padding: 14px 36px; margin-right: 4px; border-top-left-radius: 12px; border-top-right-radius: 12px; font-size: 18px; font-weight: bold; min-width: 120px; max-width: 300px; } QTabBar::tab:selected { background: #0078d4; color: white; } QTabBar::tab:hover { background: #e0e0e0; } QTabBar::tab:selected:hover { background: #0078d4; } ''')
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget(); self.tab_widget.setStyleSheet("QTabWidget::pane { border: none; }")
        self.log_widget = LogWidget()
        self.home_tab = HomeTab(); self.config_tab = ConfigTab(); self.project_tab = ProjectTab()
        self.tab_widget.addTab(self.home_tab, "首页"); self.tab_widget.addTab(self.config_tab, "配置"); self.tab_widget.addTab(self.project_tab, "项目")
        self.tab_widget.tabBarClicked.connect(self.on_tab_bar_clicked); self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)
        log_label = QLabel("日志"); log_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold)); log_label.setStyleSheet("color: #333; margin: 10px 0 5px 0;"); main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_widget); self.setLayout(main_layout)
        log_util.add_ui_handler(self.log_widget.append_log)
        log_util.info("UI", "应用程序UI已加载，正在初始化后端...")
        self.tab_widget.tabBar().installEventFilter(self); self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def start_backend_initialization(self):
        self.init_thread = BackendInitializationThread(self.controller)
        self.init_thread.initialization_done.connect(self.on_backend_initialized)
        self.init_thread.start()

    def on_backend_initialized(self, success, message):
        log_util.info("UI", f"后端初始化结果: {message}")
        if success:
            self.project_tab.populate_projects(self.controller.projects); log_util.info("UI", "项目选项卡已更新.")
        else: QMessageBox.critical(self, "后端初始化失败", message)
        
    def on_tab_bar_clicked(self, index):
        if index == self.tab_widget.currentIndex(): return
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing: widget.exit_edit_mode()
        self.tab_widget.setCurrentIndex(index)
        
    def on_tab_changed(self, index):
        pass
    
    def closeEvent(self, event):
        log_util.info("UI", "应用程序正在关闭，开始释放后端资源...")
        self.controller.shutdown()
        log_util.shutdown()
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing: widget.exit_edit_mode()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("S1mpleWeb3Tool"); app.setApplicationVersion("1.0.0"); app.setOrganizationName("S1mpleWeb3Tool")
    window = MyToolApplication(); window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()