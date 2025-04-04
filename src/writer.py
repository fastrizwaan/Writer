#!/usr/bin/env python3
import sys
import os
import gi
import re
import base64
import mimetypes
import json
import datetime

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, GLib, Gio, WebKit, GObject, Gdk, Pango

class Writer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.fastrizwaan.Writer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self.on_activate)
        self.current_file = None
        self.modified = False
        self.recent_files = []
        self.max_recent_files = 5
        self.zoom_level = 1.0

    def on_activate(self, app):
        # Create the main window
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_default_size(900, 700)
        self.win.set_title("Writer")
        
        # Create main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(self.main_box)
        
        # Create header bar
        self.create_header_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create editor area
        self.create_editor()
        
        # Create status bar (but don't add it yet - we'll add it after all other elements)
        self.create_status_bar()
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Initialize extra features
        self.initialize_extras()
        
        # Now add the status bar last to ensure it's at the bottom
        self.main_box.append(self.status_bar)
        
        # Load recent file list
        self.load_recent_files()
        
        # Show all
        self.win.present()
        
    def create_header_bar(self):
        """Create the header bar with file operations"""
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)
        
        # File menu
        file_menu = Gio.Menu.new()
        file_menu.append("New", "app.new")
        file_menu.append("Open", "app.open")
        file_menu.append("Save", "app.save")
        file_menu.append("Save As", "app.save_as")
        
        # Add separator
        file_menu.append("───────────", None)
        
        # Recent files submenu
        self.recent_menu = Gio.Menu.new()
        recent_section = Gio.Menu.new()
        recent_section.append_submenu("Recent Files", self.recent_menu)
        file_menu.append_section(None, recent_section)
        
        # Add Print and Exit options
        file_menu.append("───────────", None)
        file_menu.append("Print", "app.print")
        file_menu.append("Exit", "app.exit")
        
        # Create the menu button
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(file_menu)
        self.header.pack_end(self.menu_button)
        
        # Add actions
        self.create_action("new", self.on_new_clicked)
        self.create_action("open", self.on_open_clicked)
        self.create_action("save", self.on_save_clicked)
        self.create_action("save_as", self.on_save_as_clicked)
        self.create_action("print", self.on_print_clicked)
        self.create_action("exit", self.on_exit_clicked)
        
        # Document title label
        self.title_label = Gtk.Label(label="Untitled")
        self.header.set_title_widget(self.title_label)
        
        # Create Edit menu
        self.edit_menu = Gio.Menu.new()
        self.edit_menu.append("Undo", "app.undo")
        self.edit_menu.append("Redo", "app.redo")
        self.edit_menu.append("───────────", None)
        self.edit_menu.append("Cut", "app.cut")
        self.edit_menu.append("Copy", "app.copy")
        self.edit_menu.append("Paste", "app.paste")
        self.edit_menu.append("───────────", None)
        self.edit_menu.append("Find", "app.find")
        self.edit_menu.append("Select All", "app.select_all")
        
        # Add Edit menu button to header bar
        edit_button = Gtk.MenuButton()
        edit_button.set_label("Edit")
        edit_button.set_menu_model(self.edit_menu)
        self.header.pack_start(edit_button)
        
        # Create Insert menu
        self.insert_menu = Gio.Menu.new()
        self.insert_menu.append("Table...", "app.insert_table")
        self.insert_menu.append("Image...", "app.insert_image")
        self.insert_menu.append("Date/Time", "app.insert_datetime")
        
        # Add Insert menu button to header bar
        insert_button = Gtk.MenuButton()
        insert_button.set_label("Insert")
        insert_button.set_menu_model(self.insert_menu)
        self.header.pack_start(insert_button)
        
        # Create View menu
        view_menu = Gio.Menu.new()
        view_menu.append("Zoom In", "app.zoom_in")
        view_menu.append("Zoom Out", "app.zoom_out")
        view_menu.append("Reset Zoom", "app.zoom_reset")
        view_menu.append("───────────", None)
        view_menu.append("Toggle RTL Mode", "app.toggle_rtl")
        
        # Add View menu button
        view_button = Gtk.MenuButton()
        view_button.set_label("View")
        view_button.set_menu_model(view_menu)
        self.header.pack_start(view_button)
        
        # Create Format menu
        format_menu = Gio.Menu.new()
        format_menu.append("Paragraph Spacing...", "app.paragraph_spacing")
        format_menu.append("Line Spacing...", "app.line_spacing")
        
        # Add Format menu button
        format_button = Gtk.MenuButton()
        format_button.set_label("Format")
        format_button.set_menu_model(format_menu)
        self.header.pack_start(format_button)
        
    def create_toolbar(self):
        """Create the formatting toolbar"""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        toolbar.add_css_class("toolbar")
        self.main_box.append(toolbar)
        
        # Font family - using FontDialogButton for GTK4
        self.font_button = Gtk.FontDialogButton()
        self.font_button.set_dialog(Gtk.FontDialog.new())
        self.font_button.connect("notify::font-desc", self.on_font_changed)
        toolbar.append(self.font_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Bold
        self.bold_button = Gtk.ToggleButton()
        self.bold_button.set_icon_name("format-text-bold-symbolic")
        self.bold_button.set_tooltip_text("Bold")
        self.bold_button.connect("toggled", self.on_bold_toggled)
        toolbar.append(self.bold_button)
        
        # Italic
        self.italic_button = Gtk.ToggleButton()
        self.italic_button.set_icon_name("format-text-italic-symbolic")
        self.italic_button.set_tooltip_text("Italic")
        self.italic_button.connect("toggled", self.on_italic_toggled)
        toolbar.append(self.italic_button)
        
        # Underline
        self.underline_button = Gtk.ToggleButton()
        self.underline_button.set_icon_name("format-text-underline-symbolic")
        self.underline_button.set_tooltip_text("Underline")
        self.underline_button.connect("toggled", self.on_underline_toggled)
        toolbar.append(self.underline_button)
        
        # Strikethrough
        self.strikethrough_button = Gtk.ToggleButton()
        self.strikethrough_button.set_icon_name("format-text-strikethrough-symbolic")
        self.strikethrough_button.set_tooltip_text("Strikethrough")
        self.strikethrough_button.connect("toggled", self.on_strikethrough_toggled)
        toolbar.append(self.strikethrough_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Superscript
        self.superscript_button = Gtk.ToggleButton()
        self.superscript_button.set_icon_name("format-text-superscript-symbolic")
        self.superscript_button.set_tooltip_text("Superscript")
        self.superscript_button.connect("toggled", self.on_superscript_toggled)
        toolbar.append(self.superscript_button)
        
        # Subscript
        self.subscript_button = Gtk.ToggleButton()
        self.subscript_button.set_icon_name("format-text-subscript-symbolic")
        self.subscript_button.set_tooltip_text("Subscript")
        self.subscript_button.connect("toggled", self.on_subscript_toggled)
        toolbar.append(self.subscript_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Alignment
        self.align_left_button = Gtk.ToggleButton()
        self.align_left_button.set_icon_name("format-justify-left-symbolic")
        self.align_left_button.set_tooltip_text("Align Left")
        self.align_left_button.connect("toggled", self.on_align_left_toggled)
        toolbar.append(self.align_left_button)
        
        self.align_center_button = Gtk.ToggleButton()
        self.align_center_button.set_icon_name("format-justify-center-symbolic")
        self.align_center_button.set_tooltip_text("Align Center")
        self.align_center_button.connect("toggled", self.on_align_center_toggled)
        toolbar.append(self.align_center_button)
        
        self.align_right_button = Gtk.ToggleButton()
        self.align_right_button.set_icon_name("format-justify-right-symbolic")
        self.align_right_button.set_tooltip_text("Align Right")
        self.align_right_button.connect("toggled", self.on_align_right_toggled)
        toolbar.append(self.align_right_button)
        
        self.align_justify_button = Gtk.ToggleButton()
        self.align_justify_button.set_icon_name("format-justify-fill-symbolic")
        self.align_justify_button.set_tooltip_text("Justify")
        self.align_justify_button.connect("toggled", self.on_align_justify_toggled)
        toolbar.append(self.align_justify_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Text color
        self.text_color_button = Gtk.ColorButton()
        self.text_color_button.set_tooltip_text("Text Color")
        self.text_color_button.connect("color-set", self.on_text_color_changed)
        toolbar.append(self.text_color_button)
        
        # Background color
        self.bg_color_button = Gtk.ColorButton()
        self.bg_color_button.set_tooltip_text("Background Color")
        self.bg_color_button.connect("color-set", self.on_bg_color_changed)
        toolbar.append(self.bg_color_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Bullet list
        self.bullet_list_button = Gtk.ToggleButton()
        self.bullet_list_button.set_icon_name("view-list-bullet-symbolic")
        self.bullet_list_button.set_tooltip_text("Bullet List")
        self.bullet_list_button.connect("toggled", self.on_bullet_list_toggled)
        toolbar.append(self.bullet_list_button)
        
        # Numbered list
        self.numbered_list_button = Gtk.ToggleButton()
        self.numbered_list_button.set_icon_name("view-list-ordered-symbolic")
        self.numbered_list_button.set_tooltip_text("Numbered List")
        self.numbered_list_button.connect("toggled", self.on_numbered_list_toggled)
        toolbar.append(self.numbered_list_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Indent
        self.indent_button = Gtk.Button()
        self.indent_button.set_icon_name("format-indent-more-symbolic")
        self.indent_button.set_tooltip_text("Increase Indent")
        self.indent_button.connect("clicked", self.on_indent_clicked)
        toolbar.append(self.indent_button)
        
        # Outdent
        self.outdent_button = Gtk.Button()
        self.outdent_button.set_icon_name("format-indent-less-symbolic")
        self.outdent_button.set_tooltip_text("Decrease Indent")
        self.outdent_button.connect("clicked", self.on_outdent_clicked)
        toolbar.append(self.outdent_button)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # RTL mode toggle
        self.rtl_button = Gtk.ToggleButton()
        self.rtl_button.set_icon_name("format-text-direction-rtl-symbolic")
        self.rtl_button.set_tooltip_text("Right to Left Text")
        self.rtl_button.connect("toggled", self.on_rtl_toggled)
        toolbar.append(self.rtl_button)
        
        # Make the toolbar look nice
        toolbar.add_css_class("toolbar")
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        
        # Add a separator before the zoom button
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Insert Table button
        self.insert_table_button = Gtk.Button()
        self.insert_table_button.set_icon_name("insert-table-symbolic")
        self.insert_table_button.set_tooltip_text("Insert Table")
        self.insert_table_button.connect("clicked", lambda btn: self.on_insert_table_clicked(None, None))
        toolbar.append(self.insert_table_button)
        
        # Insert Image button
        self.insert_image_button = Gtk.Button()
        self.insert_image_button.set_icon_name("insert-image-symbolic")
        self.insert_image_button.set_tooltip_text("Insert Image")
        self.insert_image_button.connect("clicked", lambda btn: self.on_insert_image_clicked(None, None))
        toolbar.append(self.insert_image_button)
        
        # Insert Date/Time button
        self.insert_datetime_button = Gtk.Button()
        self.insert_datetime_button.set_icon_name("insert-datetime-symbolic")
        self.insert_datetime_button.set_tooltip_text("Insert Date/Time")
        self.insert_datetime_button.connect("clicked", lambda btn: self.on_insert_datetime_clicked(None, None))
        toolbar.append(self.insert_datetime_button)  
              
        # Zoom button with accessibility icon
        self.zoom_button = Gtk.MenuButton()
        self.zoom_button.set_icon_name("org.gnome.Settings-accessibility-zoom-symbolic")
        self.zoom_button.set_tooltip_text("Zoom")
        toolbar.append(self.zoom_button)
        
        # Create a popover for the zoom slider
        self.zoom_popover = Gtk.Popover()
        self.zoom_button.set_popover(self.zoom_popover)
        
        # Create a vertical box for the popover content
        zoom_popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        zoom_popover_box.set_margin_top(0)
        zoom_popover_box.set_margin_bottom(0)
        zoom_popover_box.set_margin_start(0)
        zoom_popover_box.set_margin_end(0)
        
        # Add zoom percentage label
        self.zoom_label = Gtk.Label(label="100%")
        self.zoom_label.set_margin_bottom(6)
        zoom_popover_box.append(self.zoom_label)
        
        # Add vertical zoom slider
        zoom_adjustment = Gtk.Adjustment.new(
            value=1.0,             # Initial value (100%)
            lower=0.5,             # Minimum (20%)
            upper=7.0,             # Maximum (500%)
            step_increment=0.1,    # Small step
            page_increment=0.5,    # Page step
            page_size=0            # Not a scrollbar
        )
        
        self.zoom_slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=zoom_adjustment)
        self.zoom_slider.set_draw_value(False)  # Don't draw value on slider
        self.zoom_slider.set_inverted(True)     # 500% at top, 20% at bottom
        self.zoom_slider.set_size_request(-1, 150)  # Height of 150px
        
        # Connect value-changed signal and store handler ID for later blocking
        self.zoom_slider_handler_id = self.zoom_slider.connect("value-changed", self.on_zoom_slider_changed)
        zoom_popover_box.append(self.zoom_slider)
        
        # Add reset button (100%)
        reset_button = Gtk.Button.new_with_label("1:1")
        reset_button.connect("clicked", self.on_zoom_reset_button_clicked)
        reset_button.set_margin_top(6)
        zoom_popover_box.append(reset_button)
        
        # Set the popover content
        self.zoom_popover.set_child(zoom_popover_box)
        
        # Make the toolbar look nice
        toolbar.add_css_class("toolbar")
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)


    def on_zoom_slider_changed(self, slider):
        """Handle zoom slider value change"""
        self.zoom_level = slider.get_value()
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update zoom label
        self.zoom_label.set_text(f"{int(self.zoom_level * 100)}%")
        
        # Update status
        self.status_label.set_text(f"Zoom: {int(self.zoom_level * 100)}%")

    # 3. Update the zoom reset button handler
    def on_zoom_reset_button_clicked(self, button):
        """Handle zoom reset button click"""
        self.zoom_level = 1.0
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update zoom label in popover
        self.zoom_label.set_text("100%")
        
        # Update status
        self.status_label.set_text("Zoom: 100%")
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)
        
        # Close the popover
        self.zoom_popover.popdown()


    # Also, update the create_toolbar method to ensure the zoom percentage label is correctly styled
    def create_toolbar_zoom_button(self, toolbar):
        """Create the zoom button and its popover in the toolbar"""
        # Add a separator before the zoom button
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.append(separator)
        
        # Zoom button with accessibility icon
        self.zoom_button = Gtk.MenuButton()
        self.zoom_button.set_icon_name("org.gnome.Settings-accessibility-zoom-symbolic")
        self.zoom_button.set_tooltip_text("Zoom")
        toolbar.append(self.zoom_button)
        
        # Create a popover for the zoom slider
        self.zoom_popover = Gtk.Popover()
        self.zoom_button.set_popover(self.zoom_popover)
        
        # Create a vertical box for the popover content
        zoom_popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        zoom_popover_box.set_margin_top(12)
        zoom_popover_box.set_margin_bottom(12)
        zoom_popover_box.set_margin_start(12)
        zoom_popover_box.set_margin_end(12)
        
        # Add zoom percentage label with proper styling
        self.zoom_label = Gtk.Label(label=f"{int(self.zoom_level * 100)}%")
        self.zoom_label.set_margin_bottom(6)
        self.zoom_label.add_css_class("title-4")  # Make it stand out with a title style
        self.zoom_label.set_halign(Gtk.Align.CENTER)
        zoom_popover_box.append(self.zoom_label)
        
        # Add vertical zoom slider
        zoom_adjustment = Gtk.Adjustment.new(
            value=self.zoom_level,  # Use current zoom level
            lower=0.2,             # Minimum (20%)
            upper=5.0,             # Maximum (500%)
            step_increment=0.1,    # Small step
            page_increment=0.5,    # Page step
            page_size=0            # Not a scrollbar
        )
        
        self.zoom_slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=zoom_adjustment)
        self.zoom_slider.set_draw_value(False)  # Don't draw value on slider
        self.zoom_slider.set_inverted(True)     # 500% at top, 20% at bottom
        self.zoom_slider.set_size_request(-1, 150)  # Height of 150px
        self.zoom_slider.set_halign(Gtk.Align.CENTER)
        
        # Connect value-changed signal and store handler ID for later blocking
        self.zoom_slider_handler_id = self.zoom_slider.connect("value-changed", self.on_zoom_slider_changed)
        zoom_popover_box.append(self.zoom_slider)
        
        # Add reset button (100%)
        reset_button = Gtk.Button.new_with_label("Reset to 100%")
        reset_button.connect("clicked", self.on_zoom_reset_button_clicked)
        reset_button.set_margin_top(6)
        reset_button.set_halign(Gtk.Align.CENTER)
        zoom_popover_box.append(reset_button)
        
        # Set the popover content
        self.zoom_popover.set_child(zoom_popover_box)

    # 4. Update the zoom keyboard shortcuts to work with the new zoom control
    def on_zoom_in(self, action, param):
        """Handle Zoom In command (keyboard shortcut)"""
        self.zoom_level = min(5.0, self.zoom_level + 0.1)
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update zoom label in popover
        self.zoom_label.set_text(f"{int(self.zoom_level * 100)}%")
        
        # Update status
        self.status_label.set_text(f"Zoom: {int(self.zoom_level * 100)}%")
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)


    def on_zoom_out(self, action, param):
        """Handle Zoom Out command (keyboard shortcut)"""
        self.zoom_level = max(0.2, self.zoom_level - 0.1)
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update zoom label in popover
        self.zoom_label.set_text(f"{int(self.zoom_level * 100)}%")
        
        # Update status
        self.status_label.set_text(f"Zoom: {int(self.zoom_level * 100)}%")
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)

    def on_zoom_reset(self, action, param):
        """Handle Reset Zoom command (keyboard shortcut)"""
        self.zoom_level = 1.0
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update zoom label if popover is visible
        self.zoom_label.set_text("100%")
        
        # Update status
        self.status_label.set_text("Zoom: 100%")
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)

    def create_editor(self):
        """Create the WebKit-based rich text editor with improved initialization"""
        # Scrolled window for the editor
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.main_box.append(scrolled)
        
        # WebKit WebView for rich text editing
        self.webview = WebKit.WebView()
        scrolled.set_child(self.webview)
        
        # Enable developer tools for debugging
        settings = self.webview.get_settings()
        if hasattr(settings, 'set_enable_developer_extras'):
            settings.set_enable_developer_extras(True)
        
        # Set up the WebView for rich text editing
        self.webview.load_html(self.get_editor_html(), None)
        
        # Connect selection change signals
        self.webview.connect("load-changed", self.on_load_changed)
        
        # Handle content changes
        self.webview.connect("notify::estimated-load-progress", self.on_progress_change)
    def get_editor_html(self):
        """Return the HTML for the editor using a raw string to avoid escape sequence issues"""
        return r"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: sans-serif;
                    margin: 10px;
                    min-height: 100vh;
                }
                #editor {
                    border: none;
                    outline: none;
                    padding: 10px;
                    min-height: calc(100vh - 80px);
                }
                table {
                    border-collapse: collapse;
                    margin: 10px 0;
                    position: relative;
                    resize: both;
                    overflow: auto;
                    min-width: 30px;
                    min-height: 30px;
                }
                table.left-align {
                    float: left;
                    margin-right: 10px;
                    clear: none;
                }
                table.right-align {
                    float: right;
                    margin-left: 10px;
                    clear: none;
                }
                table.center-align {
                    margin-left: auto;
                    margin-right: auto;
                    float: none;
                    clear: both;
                }
                table.no-wrap {
                    float: none;
                    clear: both;
                    width: 100%;
                }
                table td {
                    border: 1px solid #ccc;
                    padding: 5px;
                    min-width: 30px;
                    position: relative;
                }
                table th {
                    border: 1px solid #ccc;
                    padding: 5px;
                    min-width: 30px;
                    background-color: #f0f0f0;
                }
                .table-drag-handle {
                    position: absolute;
                    top: -16px;
                    left: -1px;
                    width: 16px;
                    height: 16px;
                    background-color: #4e9eff;
                    border-radius: 2px;
                    cursor: ns-resize;
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 10px;
                }
                .table-handle {
                    position: absolute;
                    bottom: -10px;
                    right: -10px;
                    width: 16px;
                    height: 16px;
                    background-color: #4e9eff;
                    border-radius: 8px;
                    cursor: nwse-resize;
                    z-index: 1000;
                }
                img {
                    max-width: 100%;
                }
                .search-highlight {
                    background-color: #FFFF00;
                }
                .rtl {
                    direction: rtl;
                    text-align: right;
                }
                div, p {
                    overflow: hidden;
                }
            </style>
            <script>
                var searchResults = [];
                var searchIndex = -1;
                var currentSearchText = "";
                var activeTable = null;
                var isDragging = false;
                var dragStartX = 0;
                var dragStartY = 0;
                var tableStartX = 0;
                var tableStartY = 0;
                var isResizing = false;
                
            // Initialize history variables 
                var editorHistory = [];
                var historyIndex = -1;
                var isPerformingUndoRedo = false;

                // Create a better history entry creation function
                function createHistoryEntry() {
                    // Don't create entry if we're in the middle of an undo/redo operation
                    if (isPerformingUndoRedo) return;
                    
                    // Get editor content
                    let editorContent = document.getElementById('editor').innerHTML;
                    
                    // Save selection as a range of character offsets within the editor
                    let selectionInfo = saveSelection();
                    
                    let historyEntry = {
                        content: editorContent,
                        selection: selectionInfo,
                        timestamp: Date.now()
                    };
                    
                    // Trim history if navigating from middle point
                    if (historyIndex >= 0 && historyIndex < editorHistory.length - 1) {
                        editorHistory = editorHistory.slice(0, historyIndex + 1);
                    }
                    
                    // Add current state to history
                    editorHistory.push(historyEntry);
                    historyIndex = editorHistory.length - 1;
                    
                    // Debug
                    console.log("History entry created. Total:", editorHistory.length, "Current:", historyIndex);
                }

                // Save selection as character offsets
                function saveSelection() {
                    const editor = document.getElementById('editor');
                    const selection = window.getSelection();
                    
                    if (!selection.rangeCount) return null;
                    
                    const range = selection.getRangeAt(0);
                    
                    // Get total text content
                    const editorText = editor.textContent;
                    
                    // Use a temporary range to measure character offsets
                    const tempRange = document.createRange();
                    tempRange.setStart(editor, 0);
                    tempRange.setEnd(range.startContainer, range.startOffset);
                    const startOffset = tempRange.toString().length;
                    
                    // If selection is collapsed (just cursor), end offset is same as start
                    let endOffset;
                    if (range.collapsed) {
                        endOffset = startOffset;
                    } else {
                        tempRange.setEnd(range.endContainer, range.endOffset);
                        endOffset = tempRange.toString().length;
                    }
                    
                    return {
                        start: startOffset,
                        end: endOffset,
                        collapsed: range.collapsed
                    };
                }

                // Restore selection from saved character offsets
                function restoreSelection(selectionInfo) {
                    if (!selectionInfo) return false;
                    
                    const editor = document.getElementById('editor');
                    const editorText = editor.textContent;
                    
                    // Validate offsets against current content length
                    const maxOffset = editorText.length;
                    const startOffset = Math.min(selectionInfo.start, maxOffset);
                    const endOffset = Math.min(selectionInfo.end, maxOffset);
                    
                    // Find the nodes and offsets corresponding to character positions
                    const startPosition = getNodeAndOffsetAtCharacterOffset(editor, startOffset);
                    const endPosition = getNodeAndOffsetAtCharacterOffset(editor, endOffset);
                    
                    if (!startPosition || !endPosition) {
                        console.error("Failed to find position for offsets:", startOffset, endOffset);
                        return false;
                    }
                    
                    try {
                        // Create a range and set it as the current selection
                        const range = document.createRange();
                        range.setStart(startPosition.node, startPosition.offset);
                        range.setEnd(endPosition.node, endPosition.offset);
                        
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                        
                        // Ensure cursor is visible
                        if (startPosition.node.nodeType === Node.TEXT_NODE) {
                            startPosition.node.parentNode.scrollIntoView({ behavior: 'auto', block: 'center' });
                        } else {
                            startPosition.node.scrollIntoView({ behavior: 'auto', block: 'center' });
                        }
                        
                        return true;
                    } catch (e) {
                        console.error("Error restoring selection:", e);
                        return false;
                    }
                }

                // Find node and offset at a given character position in the editor
                function getNodeAndOffsetAtCharacterOffset(root, charOffset) {
                    const walker = document.createTreeWalker(
                        root,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let currentOffset = 0;
                    let node = walker.nextNode();
                    
                    while (node) {
                        const nodeLength = node.nodeValue.length;
                        
                        if (currentOffset + nodeLength >= charOffset) {
                            return {
                                node: node,
                                offset: charOffset - currentOffset
                            };
                        }
                        
                        currentOffset += nodeLength;
                        node = walker.nextNode();
                    }
                    
                    // If we couldn't find the exact position, return the last position
                    if (root.lastChild) {
                        const lastNode = root.lastChild;
                        return {
                            node: lastNode.nodeType === Node.TEXT_NODE ? lastNode : root,
                            offset: lastNode.nodeType === Node.TEXT_NODE ? lastNode.nodeValue.length : root.childNodes.length
                        };
                    }
                    
                    // Fallback to the root node
                    return {
                        node: root,
                        offset: 0
                    };
                }

                // Improved undo function
                function customUndo() {
                    console.log("Custom Undo called. Current index:", historyIndex, "History length:", editorHistory.length);
                    
                    if (editorHistory.length === 0 || historyIndex <= 0) {
                        console.log("Nothing to undo - at beginning of history or no history");
                        return false;
                    }
                    
                    // Flag that we are performing undo/redo to prevent new history entries
                    isPerformingUndoRedo = true;
                    
                    try {
                        // Go back one step in history
                        historyIndex--;
                        let historyEntry = editorHistory[historyIndex];
                        
                        // Get the editor
                        const editor = document.getElementById('editor');
                        
                        // Restore content
                        editor.innerHTML = historyEntry.content;
                        
                        // Restore selection if available
                        if (historyEntry.selection) {
                            setTimeout(() => {
                                restoreSelection(historyEntry.selection);
                            }, 0);
                        }
                        
                        // Notify content changed
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        console.log("Undo complete. Now at index:", historyIndex);
                        return true;
                    } catch (e) {
                        console.error("Error during undo:", e);
                        return false;
                    } finally {
                        // Reset the flag
                        setTimeout(() => {
                            isPerformingUndoRedo = false;
                        }, 10);
                    }
                }

                // Improved redo function
                function customRedo() {
                    console.log("Custom Redo called. Current index:", historyIndex, "History length:", editorHistory.length);
                    
                    if (editorHistory.length === 0 || historyIndex >= editorHistory.length - 1) {
                        console.log("Nothing to redo - at end of history or no history");
                        return false;
                    }
                    
                    // Flag that we are performing undo/redo to prevent new history entries
                    isPerformingUndoRedo = true;
                    
                    try {
                        // Go forward one step in history
                        historyIndex++;
                        let historyEntry = editorHistory[historyIndex];
                        
                        // Get the editor
                        const editor = document.getElementById('editor');
                        
                        // Restore content
                        editor.innerHTML = historyEntry.content;
                        
                        // Restore selection if available
                        if (historyEntry.selection) {
                            setTimeout(() => {
                                restoreSelection(historyEntry.selection);
                            }, 0);
                        }
                        
                        // Notify content changed
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        console.log("Redo complete. Now at index:", historyIndex);
                        return true;
                    } catch (e) {
                        console.error("Error during redo:", e);
                        return false;
                    } finally {
                        // Reset the flag
                        setTimeout(() => {
                            isPerformingUndoRedo = false;
                        }, 10);
                    }
                }

                // Update replaceSelection function to create history entries
                function replaceSelection(replaceText) {
                    if (searchResults.length === 0 || searchIndex < 0) return false;
                    
                    // Create history entry before change
                    createHistoryEntry();
                    
                    // Now perform the replacement
                    let span = searchResults[searchIndex];
                    let range = document.createRange();
                    range.selectNodeContents(span);
                    
                    let selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // Replace the text
                    document.execCommand('insertText', false, replaceText);
                    
                    // Create another history entry after the change
                    setTimeout(() => {
                        createHistoryEntry();
                    }, 0);
                    
                    // Mark document as modified
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                    
                    // Need to rebuild the search results
                    let searchText = currentSearchText;
                    setTimeout(() => {
                        searchAndHighlight(searchText);
                    }, 10);
                    
                    return true;
                }

                // Update replaceAll function to create history entries
                function replaceAll(searchText, replaceText) {
                    if (!searchText) return 0;
                    
                    // Create history entry before change
                    createHistoryEntry();
                    
                    // First clear any existing search
                    clearSearch();
                    
                    let editor = document.getElementById('editor');
                    let content = editor.innerHTML;
                    
                    // Escape special characters for regex
                    let escapedSearch = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    let regexSearch = new RegExp(escapedSearch, 'g');
                    
                    // Replace all occurrences
                    let newContent = content.replace(regexSearch, replaceText);
                    
                    // Count how many replacements were made
                    let count = 0;
                    let tempCount = (content.match(regexSearch) || []).length;
                    count = tempCount;
                    
                    // Update editor content
                    editor.innerHTML = newContent;
                    
                    // Create another history entry after the change
                    setTimeout(() => {
                        createHistoryEntry();
                    }, 0);
                    
                    // Mark document as modified
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                    
                    return count;
                }

                // Make sure to add this to your document ready function
                document.addEventListener('DOMContentLoaded', function() {
                    const editor = document.getElementById('editor');
                    
                    if (editor.innerHTML.trim() === '') {
                        editor.innerHTML = '<div><br></div>';
                    }
                    
                    // Add input listener to capture regular edits
                    editor.addEventListener('input', function(e) {
                        // Don't create history for programmatic changes during undo/redo
                        if (!isPerformingUndoRedo) {
                            createHistoryEntry();
                        }
                    });
                    
                    // Create initial history entry
                    setTimeout(() => {
                        createHistoryEntry();
                    }, 100);
                    
                    // Other event listeners...
                    
                    // Add keyboard shortcut handlers for undo/redo
                    editor.addEventListener('keydown', function(e) {
                        if (e.key === 'z' && e.ctrlKey && !e.shiftKey) {
                            // Ctrl+Z (Undo)
                            e.preventDefault();
                            customUndo();
                        } else if ((e.key === 'z' && e.ctrlKey && e.shiftKey) || 
                                (e.key === 'y' && e.ctrlKey)) {
                            // Ctrl+Shift+Z or Ctrl+Y (Redo)
                            e.preventDefault();
                            customRedo();
                        }
                    });
                });

                // Add debugging function
                function debugHistory() {
                    console.log({
                        historyLength: editorHistory.length,
                        currentIndex: historyIndex,
                        isPerformingUndoRedo: isPerformingUndoRedo,
                        currentContent: document.getElementById('editor').innerHTML.substring(0, 100) + '...'
                    });
                    return true;
                }
                document.addEventListener('DOMContentLoaded', function() {
                    const editor = document.getElementById('editor');
                    if (editor.innerHTML.trim() === '') {
                        editor.innerHTML = '<div><br></div>';
                    }
                    
                    editor.addEventListener('input', function() {
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                    });
                    
                    editor.addEventListener('selectionchange', function() {
                        let isBold = document.queryCommandState('bold');
                        let isItalic = document.queryCommandState('italic');
                        let isUnderline = document.queryCommandState('underline');
                        let isStrikethrough = document.queryCommandState('strikeThrough');
                        let alignment = '';
                        
                        if (document.queryCommandState('justifyLeft')) alignment = 'left';
                        if (document.queryCommandState('justifyCenter')) alignment = 'center';
                        if (document.queryCommandState('justifyRight')) alignment = 'right';
                        if (document.queryCommandState('justifyFull')) alignment = 'justify';
                        
                        let selection = window.getSelection();
                        let isSuperscript = false;
                        let isSubscript = false;
                        
                        if (selection.rangeCount > 0) {
                            let range = selection.getRangeAt(0);
                            let container = range.commonAncestorContainer;
                            if (container.nodeType === 3) {
                                container = container.parentNode;
                            }
                            let parent = container;
                            while (parent && parent !== document.body) {
                                if (parent.tagName === 'SUP') isSuperscript = true;
                                if (parent.tagName === 'SUB') isSubscript = true;
                                parent = parent.parentNode;
                            }
                        }
                        
                        window.webkit.messageHandlers.selectionChanged.postMessage(
                            JSON.stringify({
                                bold: isBold,
                                italic: isItalic,
                                underline: isUnderline,
                                strikethrough: isStrikethrough,
                                superscript: isSuperscript,
                                subscript: isSubscript,
                                alignment: alignment
                            })
                        );
                    });
                    
                    editor.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            const selection = window.getSelection();
                            if (selection.rangeCount > 0) {
                                const range = selection.getRangeAt(0);
                                const startNode = range.startContainer;
                                if (startNode === editor || 
                                    (startNode.nodeType === Node.TEXT_NODE && startNode.parentNode === editor)) {
                                    e.preventDefault();
                                    document.execCommand('insertHTML', false, '<div><br></div>');
                                }
                            }
                        }
                    });
                    
                    setupTableEventHandlers();
                });

                function setupTableEventHandlers() {
                    const editor = document.getElementById('editor');
                    
                    editor.addEventListener('mousedown', function(e) {
                        let tableElement = findParentTable(e.target);
                        if (e.target.classList.contains('table-drag-handle')) {
                            if (e.button === 0) {
                                startTableDrag(e, findParentTable(e.target));
                            }
                        }
                        if (e.target.classList.contains('table-handle')) {
                            startTableResize(e, findParentTable(e.target));
                        }
                    });
                    
                    document.addEventListener('mousemove', function(e) {
                        if (isDragging && activeTable) {
                            moveTable(e);
                        }
                        if (isResizing && activeTable) {
                            resizeTable(e);
                        }
                    });
                    
                    document.addEventListener('mouseup', function() {
                        if (isDragging || isResizing) {
                            isDragging = false;
                            isResizing = false;
                            if (activeTable) {
                                window.webkit.messageHandlers.contentChanged.postMessage('changed');
                            }
                        }
                    });
                    
                    editor.addEventListener('click', function(e) {
                        let tableElement = findParentTable(e.target);
                        if (!tableElement && activeTable) {
                            deactivateAllTables();
                        } else if (tableElement && tableElement !== activeTable) {
                            deactivateAllTables();
                            activateTable(tableElement);
                            window.webkit.messageHandlers.tableClicked.postMessage('table-clicked');
                        }
                    });
                }
                
                function findParentTable(element) {
                    while (element && element !== document.body) {
                        if (element.tagName === 'TABLE') {
                            return element;
                        }
                        element = element.parentNode;
                    }
                    return null;
                }
                
                function startTableDrag(e, tableElement) {
                    e.preventDefault();
                    if (!tableElement) return;
                    isDragging = true;
                    activeTable = tableElement;
                    dragStartX = e.clientX;
                    dragStartY = e.clientY;
                    document.body.style.cursor = 'move';
                }
                
                function moveTable(e) {
                    if (!isDragging || !activeTable) return;
                    const currentY = e.clientY;
                    const deltaY = currentY - dragStartY;
                    
                    if (Math.abs(deltaY) > 30) {
                        const editor = document.getElementById('editor');
                        const selection = window.getSelection();
                        const blocks = Array.from(editor.children).filter(node => {
                            const style = window.getComputedStyle(node);
                            return style.display.includes('block') || node.tagName === 'TABLE';
                        });
                        const tableIndex = blocks.indexOf(activeTable);
                        
                        if (deltaY < 0 && tableIndex > 0) {
                            const targetElement = blocks[tableIndex - 1];
                            editor.insertBefore(activeTable, targetElement);
                            dragStartY = currentY;
                            window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        } 
                        else if (deltaY > 0 && tableIndex < blocks.length - 1) {
                            const targetElement = blocks[tableIndex + 1];
                            if (targetElement.nextSibling) {
                                editor.insertBefore(activeTable, targetElement.nextSibling);
                            } else {
                                editor.appendChild(activeTable);
                            }
                            dragStartY = currentY;
                            window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        }
                    }
                }
                
                function startTableResize(e, tableElement) {
                    e.preventDefault();
                    isResizing = true;
                    activeTable = tableElement;
                    dragStartX = e.clientX;
                    dragStartY = e.clientY;
                    const style = window.getComputedStyle(tableElement);
                    tableStartX = parseInt(style.width) || tableElement.offsetWidth;
                    tableStartY = parseInt(style.height) || tableElement.offsetHeight;
                }
                
                function resizeTable(e) {
                    if (!isResizing || !activeTable) return;
                    const deltaX = e.clientX - dragStartX;
                    const deltaY = e.clientY - dragStartY;
                    activeTable.style.width = (tableStartX + deltaX) + 'px';
                    activeTable.style.height = (tableStartY + deltaY) + 'px';
                }
                
                function activateTable(tableElement) {
                    activeTable = tableElement;
                    tableElement.style.marginLeft = '';
                    tableElement.style.marginTop = '';
                    
                    const currentClasses = tableElement.className;
                    const alignmentClasses = ['left-align', 'right-align', 'center-align', 'no-wrap'];
                    let currentAlignment = 'no-wrap';
                    alignmentClasses.forEach(cls => {
                        if (currentClasses.includes(cls)) {
                            currentAlignment = cls;
                        }
                    });
                    
                    alignmentClasses.forEach(cls => tableElement.classList.remove(cls));
                    tableElement.classList.add(currentAlignment);
                    
                    // Only add resize and move handles
                    if (!tableElement.querySelector('.table-handle')) {
                        const resizeHandle = document.createElement('div');
                        resizeHandle.className = 'table-handle';
                        tableElement.appendChild(resizeHandle);
                    }
                    
                    if (!tableElement.querySelector('.table-drag-handle')) {
                        const dragHandle = document.createElement('div');
                        dragHandle.className = 'table-drag-handle';
                        dragHandle.innerHTML = '↕';
                        dragHandle.title = 'Drag to reposition table between paragraphs';
                        tableElement.appendChild(dragHandle);
                    }
                }
                
                function addTableRow(tableElement, position) {
                    if (!tableElement && activeTable) {
                        tableElement = activeTable;
                    }
                    
                    if (!tableElement) return;
                    
                    const rows = tableElement.rows;
                    if (rows.length > 0) {
                        // If position is provided, use it, otherwise append at the end
                        const rowIndex = (position !== undefined) ? position : rows.length;
                        const newRow = tableElement.insertRow(rowIndex);
                        for (let i = 0; i < rows[0].cells.length; i++) {
                            const cell = newRow.insertCell(i);
                            cell.innerHTML = ' ';
                        }
                    }
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                }
                
                function addTableColumn(tableElement, position) {
                    if (!tableElement && activeTable) {
                        tableElement = activeTable;
                    }
                    
                    if (!tableElement) return;
                    
                    const rows = tableElement.rows;
                    for (let i = 0; i < rows.length; i++) {
                        // If position is provided, use it, otherwise append at the end
                        const cellIndex = (position !== undefined) ? position : rows[i].cells.length;
                        const cell = rows[i].insertCell(cellIndex);
                        cell.innerHTML = ' ';
                    }
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                }

                
                function deleteTable(tableElement) {
                    if (!tableElement && activeTable) {
                        tableElement = activeTable;
                    }
                    
                    if (!tableElement) return;
                    
                    // Remove the table from the DOM
                    tableElement.parentNode.removeChild(tableElement);
                    
                    // Reset activeTable reference
                    activeTable = null;
                    
                    // Notify the app
                    window.webkit.messageHandlers.tableDeleted.postMessage('table-deleted');
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                }

                function deleteTableRow(tableElement, rowIndex) {
                    if (!tableElement && activeTable) {
                        tableElement = activeTable;
                    }
                    
                    if (!tableElement) return;
                    
                    const rows = tableElement.rows;
                    if (rows.length > 1) {
                        // If rowIndex is provided, delete that row, otherwise delete the last row
                        const indexToDelete = (rowIndex !== undefined) ? rowIndex : rows.length - 1;
                        if (indexToDelete >= 0 && indexToDelete < rows.length) {
                            tableElement.deleteRow(indexToDelete);
                        }
                    }
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                }
                
                function deleteTableColumn(tableElement, colIndex) {
                    if (!tableElement && activeTable) {
                        tableElement = activeTable;
                    }
                    
                    if (!tableElement) return;
                    
                    const rows = tableElement.rows;
                    if (rows.length > 0 && rows[0].cells.length > 1) {
                        // If colIndex is provided, delete that column, otherwise delete the last column
                        const indexToDelete = (colIndex !== undefined) ? colIndex : rows[0].cells.length - 1;
                        
                        for (let i = 0; i < rows.length; i++) {
                            if (indexToDelete >= 0 && indexToDelete < rows[i].cells.length) {
                                rows[i].deleteCell(indexToDelete);
                            }
                        }
                    }
                    window.webkit.messageHandlers.contentChanged.postMessage('changed');
                }
                // Helper function to get the currently selected cell from the current selection
                function getSelectedTableCell() {
                    const selection = window.getSelection();
                    if (selection.rangeCount < 1) return null;
                    
                    let container = selection.getRangeAt(0).startContainer;
                    
                    // If the container is a text node, get its parent
                    if (container.nodeType === 3) {
                        container = container.parentNode;
                    }
                    
                    // Find the TD or TH parent
                    while (container && container.tagName !== 'TD' && container.tagName !== 'TH') {
                        container = container.parentNode;
                        // Stop if we reach the table or document body
                        if (!container || container === activeTable || container === document.body) {
                            return null;
                        }
                    }
                    
                    return container; // Returns the TD/TH element or null
                }
                
                function deactivateAllTables() {
                    const tables = document.querySelectorAll('table');
                    tables.forEach(table => {
                        const resizeHandle = table.querySelector('.table-handle');
                        if (resizeHandle) resizeHandle.remove();
                        const dragHandle = table.querySelector('.table-drag-handle');
                        if (dragHandle) dragHandle.remove();
                    });
                    if (activeTable) {
                        activeTable = null;
                        window.webkit.messageHandlers.tablesDeactivated.postMessage('tables-deactivated');
                    }
                }
                
                function wrapUnwrappedText(element) {
                    let childNodes = Array.from(element.childNodes);
                    let textNodesToWrap = [];
                    for (let i = 0; i < childNodes.length; i++) {
                        let node = childNodes[i];
                        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                            textNodesToWrap.push(node);
                        }
                    }
                    for (let i = 0; i < textNodesToWrap.length; i++) {
                        let textNode = textNodesToWrap[i];
                        let wrapper = document.createElement('div');
                        element.replaceChild(wrapper, textNode);
                        wrapper.appendChild(textNode);
                    }
                }
                
                function setFontFamily(family) {
                    document.execCommand('fontName', false, family);
                }
                
                function setFontSize(size) {
                    document.execCommand('fontSize', false, size);
                }
                
                function setBold() {
                    document.execCommand('bold', false, null);
                }
                
                function setItalic() {
                    document.execCommand('italic', false, null);
                }
                
                function setUnderline() {
                    document.execCommand('underline', false, null);
                }
                
                function setStrikethrough() {
                    document.execCommand('strikeThrough', false, null);
                }
                
                function setSuperscript() {
                    document.execCommand('superscript', false, null);
                }
                
                function setSubscript() {
                    document.execCommand('subscript', false, null);
                }
                
                function setAlignment(align) {
                    document.execCommand('justify' + align, false, null);
                }
                
                function setTextColor(color) {
                    document.execCommand('foreColor', false, color);
                }
                
                function setBackgroundColor(color) {
                    document.execCommand('hiliteColor', false, color);
                }
                
                function insertBulletList() {
                    document.execCommand('insertUnorderedList', false, null);
                }
                
                function insertNumberedList() {
                    document.execCommand('insertOrderedList', false, null);
                }
                
                function increaseIndent() {
                    document.execCommand('indent', false, null);
                }
                
                function decreaseIndent() {
                    document.execCommand('outdent', false, null);
                }
                
                function getContent() {
                    return document.getElementById('editor').innerHTML;
                }
                
                function setContent(html) {
                    if (!html || html.trim() === '') {
                        document.getElementById('editor').innerHTML = '<div><br></div>';
                        return;
                    }
                    if (!html.trim().startsWith('<div') && 
                        !html.trim().startsWith('<p') && 
                        !html.trim().startsWith('<h') &&
                        !html.trim().startsWith('<ul') && 
                        !html.trim().startsWith('<ol') && 
                        !html.trim().startsWith('<table')) {
                        html = '<div>' + html + '</div>';
                    }
                    document.getElementById('editor').innerHTML = html;
                    setTimeout(() => {
                        wrapUnwrappedText(document.getElementById('editor'));
                        setupTableEventHandlers();
                    }, 0);
                }
                
                function getWordCount() {
                    let text = document.getElementById('editor').innerText;
                    let charCount = text.length;
                    let wordCount = 0;
                    if (text.trim()) {
                        wordCount = text.trim().split(/\s+/).filter(Boolean).length;
                    }
                    return JSON.stringify({ words: wordCount, chars: charCount });
                }
                
                function setZoom(level) {
                    document.body.style.zoom = level;
                    return true;
                }
                
                function toggleRTL() {
                    let editor = document.getElementById('editor');
                    if (editor.classList.contains('rtl')) {
                        editor.classList.remove('rtl');
                        return false;
                    } else {
                        editor.classList.add('rtl');
                        return true;
                    }
                }
                
                function insertTable(rows, cols) {
                    let table = '<table border="1" cellspacing="0" cellpadding="5" class="no-wrap" style="border-collapse: collapse;">';
                    for (let i = 0; i < rows; i++) {
                        table += '<tr>';
                        for (let j = 0; j < cols; j++) {
                            table += '<td> </td>';
                        }
                        table += '</tr>';
                    }
                    table += '</table><p></p>';
                    document.execCommand('insertHTML', false, table);
                    setTimeout(() => {
                        const tables = document.querySelectorAll('table');
                        const newTable = tables[tables.length - 1];
                        if (newTable) {
                            activateTable(newTable);
                            window.webkit.messageHandlers.tableClicked.postMessage('table-clicked');
                        }
                    }, 10);
                }
                
                function insertImageFromUrl(url) {
                    document.execCommand('insertImage', false, url);
                }
                
                function insertDateTime(format) {
                    let now = new Date();
                    let dateStr = '';
                    switch(format) {
                        case 'date':
                            dateStr = now.toLocaleDateString();
                            break;
                        case 'time':
                            dateStr = now.toLocaleTimeString();
                            break;
                        case 'datetime':
                        default:
                            dateStr = now.toLocaleString();
                            break;
                    }
                    document.execCommand('insertText', false, dateStr);
                }
                
                function doCut() {
                    document.execCommand('cut', false, null);
                }
                
                function doCopy() {
                    document.execCommand('copy', false, null);
                }
                
                function doPaste() {
                    if (navigator.clipboard && navigator.clipboard.readText) {
                        navigator.clipboard.readText()
                            .then(text => {
                                document.execCommand('insertText', false, text);
                            })
                            .catch(err => {
                                console.error('Failed to read clipboard: ', err);
                                document.execCommand('paste', false, null);
                            });
                    } else {
                        document.execCommand('paste', false, null);
                    }
                    setTimeout(() => {
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                    }, 100);
                }
                
                function selectAll() {
                    document.execCommand('selectAll', false, null);
                }
                
                // Search functions
                function clearSearch() {
                    searchResults = [];
                    searchIndex = -1;
                    currentSearchText = "";
                    
                    // Remove all highlighting
                    let editor = document.getElementById('editor');
                    let highlights = editor.querySelectorAll('.search-highlight');
                    
                    if (highlights.length) {
                        for (let i = 0; i < highlights.length; i++) {
                            let highlight = highlights[i];
                            let textNode = document.createTextNode(highlight.textContent);
                            highlight.parentNode.replaceChild(textNode, highlight);
                        }
                        editor.normalize();
                        return true;
                    }
                    return false;
                }
                
                function searchAndHighlight(searchText) {
                    // First clear any existing search
                    clearSearch();
                    
                    if (!searchText) return 0;
                    currentSearchText = searchText;
                    
                    let editor = document.getElementById('editor');
                    searchResults = [];
                    searchIndex = -1;
                    
                    // Create a TreeWalker to traverse all text nodes in the editor
                    let walker = document.createTreeWalker(
                        editor,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let matches = [];
                    let node;
                    let count = 0;
                    
                    // Find all matching text nodes
                    while ((node = walker.nextNode()) !== null) {
                        let content = node.textContent;
                        let index = content.indexOf(searchText);
                        
                        while (index !== -1) {
                            matches.push({
                                node: node,
                                index: index
                            });
                            index = content.indexOf(searchText, index + 1);
                            count++;
                        }
                    }
                    
                    // Highlight matches from last to first to maintain indices
                    for (let i = matches.length - 1; i >= 0; i--) {
                        let match = matches[i];
                        let node = match.node;
                        let index = match.index;
                        
                        // Split text node at match boundaries
                        let beforeNode = node.splitText(index);
                        let matchNode = beforeNode.splitText(searchText.length);
                        
                        // Create highlight span
                        let highlightSpan = document.createElement('span');
                        highlightSpan.className = 'search-highlight';
                        highlightSpan.style.backgroundColor = '#FFFF00';
                        
                        // Replace text node with highlight span
                        let parent = beforeNode.parentNode;
                        parent.replaceChild(highlightSpan, beforeNode);
                        highlightSpan.appendChild(beforeNode);
                        
                        // Store reference to the span
                        searchResults.push(highlightSpan);
                    }
                    
                    // Select first result if any found
                    if (searchResults.length > 0) {
                        searchIndex = 0;
                        selectSearchResult(0);
                    }
                    
                    return count;
                }
                
                function selectSearchResult(index) {
                    if (searchResults.length === 0) return false;
                    
                    // Make sure index is within bounds
                    index = Math.max(0, Math.min(index, searchResults.length - 1));
                    searchIndex = index;
                    
                    // Get the highlight span
                    let span = searchResults[index];
                    
                    // Create a range for the selection
                    let range = document.createRange();
                    range.selectNodeContents(span);
                    
                    // Apply the selection
                    let selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // Scroll to the selection
                    span.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    return true;
                }
                
                function findNext() {
                    if (searchResults.length === 0) return false;
                    
                    searchIndex++;
                    if (searchIndex >= searchResults.length) {
                        searchIndex = 0;
                    }
                    
                    return selectSearchResult(searchIndex);
                }
                
                function findPrevious() {
                    if (searchResults.length === 0) return false;
                    
                    searchIndex--;
                    if (searchIndex < 0) {
                        searchIndex = searchResults.length - 1;
                    }
                    
                    return selectSearchResult(searchIndex);
                }
                
               
                // Paragraph and line spacing functions
                function setParagraphSpacing(spacing) {
                    let selection = window.getSelection();
                    if (selection.rangeCount === 0) return false;
                    
                    let range = selection.getRangeAt(0);
                    let container = range.commonAncestorContainer;
                    
                    // Find the paragraph element
                    while (container && container.nodeType !== 1) {
                        container = container.parentNode;
                    }
                    
                    // Apply spacing to the paragraph
                    if (container && container.tagName) {
                        container.style.marginBottom = spacing + 'px';
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        return true;
                    }
                    
                    return false;
                }
                
                function setLineSpacing(spacing) {
                    let selection = window.getSelection();
                    if (selection.rangeCount === 0) return false;
                    
                    let range = selection.getRangeAt(0);
                    let container = range.commonAncestorContainer;
                    
                    // Find the paragraph element
                    while (container && container.nodeType !== 1) {
                        container = container.parentNode;
                    }
                    
                    // Apply line spacing to the paragraph
                    if (container && container.tagName) {
                        container.style.lineHeight = spacing;
                        window.webkit.messageHandlers.contentChanged.postMessage('changed');
                        return true;
                    }
                    
                    return false;
                }
            </script>
        </head>
        <body>
            <div id="editor" contenteditable="true"></div>
        </body>
        </html>
        """

    # 2. Update the on_insert_table_dialog_response method to use our enhanced table functionality

    def on_insert_table_dialog_response(self, dialog, rows, cols):
        """Handle table dialog response"""
        js_code = f"insertTable({rows}, {cols});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        self.show_table_toolbar()  # Show toolbar after insertion
        dialog.force_close()

    def format_zoom_value(self, scale, value):
        """Format the zoom value as a percentage"""
        return f"{int(value * 100)}%"

    def on_zoom_in_button_clicked(self, button):
        """Handle zoom in button click"""
        self.zoom_level = min(3.0, self.zoom_level + 0.1)
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)

    def on_zoom_out_button_clicked(self, button):
        """Handle zoom out button click"""
        self.zoom_level = max(0.5, self.zoom_level - 0.1)
        js_code = f"setZoom({self.zoom_level});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Update slider without triggering its callback
        self.zoom_slider.handler_block(self.zoom_slider_handler_id)
        self.zoom_slider.set_value(self.zoom_level)
        self.zoom_slider.handler_unblock(self.zoom_slider_handler_id)




    def create_status_bar(self):
        """Create the status bar with improved zoom slider with icons"""
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_bar.set_margin_top(8)
        self.status_bar.set_margin_bottom(8)
        self.status_bar.set_margin_start(10)
        self.status_bar.set_margin_end(10)
        
        # Status message
        self.status_label = Gtk.Label(label="Ready")
        self.status_bar.append(self.status_label)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.status_bar.append(spacer)

        # Separator before word/character counts
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.set_margin_start(6)
        separator.set_margin_end(6)
        self.status_bar.append(separator)
        
        # Word count
        self.word_count_label = Gtk.Label(label="Words: 0")
        self.status_bar.append(self.word_count_label)
        
        # Character count
        self.char_count_label = Gtk.Label(label="Characters: 0")
        self.status_bar.append(self.char_count_label)
        
        # Note: We don't append the status bar to main_box here - it will be added last in on_activate

    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Add keyboard shortcuts via actions
        self.create_action("new", self.on_new_clicked, ["<Control>n"])
        self.create_action("open", self.on_open_clicked, ["<Control>o"])
        self.create_action("save", self.on_save_clicked, ["<Control>s"])
        self.create_action("save_as", self.on_save_as_clicked, ["<Control><Shift>s"])
        self.create_action("print", self.on_print_clicked, ["<Control>p"])
        #self.create_action("print preview", none, ["none"])
        self.create_action("bold", self.on_bold_shortcut, ["<Control>b"])
        self.create_action("italic", self.on_italic_shortcut, ["<Control>i"])
        self.create_action("underline", self.on_underline_shortcut, ["<Control>u"])
        self.create_action("strikethrough", self.on_strikethrough_shortcut, ["<Control>k"])
        self.create_action("find", self.on_find_clicked, ["<Control>f"])
        self.create_action("undo", self.on_undo_clicked, ["<Control>z"])
        self.create_action("redo", self.on_redo_clicked, ["<Control><Shift>z"])
        
        # New shortcuts for additional features
        #self.create_action("select_all", self.on_select_all_clicked, ["<Control>a"])
        #self.create_action("cut", self.on_cut_clicked, ["<Control>x"])
        #self.create_action("copy", self.on_copy_clicked, ["<Control>c"])
        #self.create_action("paste", self.on_paste_clicked, ["<Control>v"])
        self.create_action("zoom_in", self.on_zoom_in, ["<Control>plus", "<Control>equal"])
        self.create_action("zoom_out", self.on_zoom_out, ["<Control>minus"])
        self.create_action("zoom_reset", self.on_zoom_reset, ["<Control>0"])
        self.create_action("toggle_rtl", self.on_toggle_rtl, ["<Control><Shift>r"])
        self.create_action("insert_datetime", self.on_insert_datetime_clicked)
        self.create_action("paragraph_spacing", self.on_paragraph_spacing_clicked)
        self.create_action("line_spacing", self.on_line_spacing_clicked)
        self.create_action("exit", self.on_exit_clicked, ["<Control>q"])

    def create_action(self, name, callback, shortcuts=None):
        """Create a GAction with optional shortcuts"""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_load_changed(self, webview, event):
        """Handle WebView load changes"""
        if event == WebKit.LoadEvent.FINISHED:
            # Set up message handlers once the WebView is loaded
            self.setup_message_handlers()

    def setup_message_handlers(self):
        """Set up WebKit message handlers for communication with JavaScript"""
        manager = self.webview.get_user_content_manager()
        
        # Register message handlers
        manager.register_script_message_handler("contentChanged")
        manager.register_script_message_handler("selectionChanged")
        manager.register_script_message_handler("tableClicked")
        manager.register_script_message_handler("tableDeleted")
        manager.register_script_message_handler("tablesDeactivated")  # New handler for deactivation
        
        # Connect signals
        manager.connect("script-message-received::contentChanged", self.on_content_changed)
        manager.connect("script-message-received::selectionChanged", self.on_selection_changed)
        manager.connect("script-message-received::tableClicked", self.on_table_clicked)
        manager.connect("script-message-received::tableDeleted", self.on_table_deleted)
        manager.connect("script-message-received::tablesDeactivated", self.on_tables_deactivated) 

    def on_content_changed(self, manager, message):
        """Handle content changes from the editor"""
        self.modified = True
        self.update_window_title()
        self.update_word_count()
        
    def on_selection_changed(self, manager, message):
        """Handle selection changes from the editor"""
        try:
            # Get selection state as JSON
            js_text = message.get_js_value().to_string()
            state = json.loads(js_text)
            
            # Update toolbar buttons without triggering their callbacks
            self.bold_button.handler_block_by_func(self.on_bold_toggled)
            self.italic_button.handler_block_by_func(self.on_italic_toggled)
            self.underline_button.handler_block_by_func(self.on_underline_toggled)
            self.strikethrough_button.handler_block_by_func(self.on_strikethrough_toggled)
            self.superscript_button.handler_block_by_func(self.on_superscript_toggled)
            self.subscript_button.handler_block_by_func(self.on_subscript_toggled)
            
            self.bold_button.set_active(state.get('bold', False))
            self.italic_button.set_active(state.get('italic', False))
            self.underline_button.set_active(state.get('underline', False))
            self.strikethrough_button.set_active(state.get('strikethrough', False))
            self.superscript_button.set_active(state.get('superscript', False))
            self.subscript_button.set_active(state.get('subscript', False))
            
            self.bold_button.handler_unblock_by_func(self.on_bold_toggled)
            self.italic_button.handler_unblock_by_func(self.on_italic_toggled)
            self.underline_button.handler_unblock_by_func(self.on_underline_toggled)
            self.strikethrough_button.handler_unblock_by_func(self.on_strikethrough_toggled)
            self.superscript_button.handler_unblock_by_func(self.on_superscript_toggled)
            self.subscript_button.handler_unblock_by_func(self.on_subscript_toggled)
            
            # Update alignment buttons
            alignment = state.get('alignment', 'left')
            self.align_left_button.handler_block_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_block_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_block_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_block_by_func(self.on_align_justify_toggled)
            
            self.align_left_button.set_active(alignment == 'left')
            self.align_center_button.set_active(alignment == 'center')
            self.align_right_button.set_active(alignment == 'right')
            self.align_justify_button.set_active(alignment == 'justify')
            
            self.align_left_button.handler_unblock_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_unblock_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_unblock_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_unblock_by_func(self.on_align_justify_toggled)
            
        except Exception as e:
            print(f"Error handling selection change: {e}")

    def on_progress_change(self, webview, param):
        """Handle WebView load progress changes"""
        progress = webview.get_estimated_load_progress()
        if progress == 1.0:
            self.update_word_count()

    def update_word_count(self):
        """Update word and character counts using fixed approach"""
        js_code = "getWordCount();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, self.handle_word_count_result)

    def handle_word_count_result(self, webview, result, user_data=None):
        """Handle word count JavaScript result with fixed approach"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                # The JavaScript now returns a pre-formatted JSON string
                json_str = js_result.to_string()
                # Remove any surrounding quotes if present
                if json_str.startswith('"') and json_str.endswith('"'):
                    json_str = json_str[1:-1].replace('\\"', '"')
                
                counts = json.loads(json_str)
                
                self.word_count_label.set_text(f"Words: {counts['words']}")
                self.char_count_label.set_text(f"Characters: {counts['chars']}")
        except Exception as e:
            print(f"Error getting word count: {e}")
            # Fallback values if counting fails
            self.word_count_label.set_text("Words: --")
            self.char_count_label.set_text("Characters: --")

    def update_window_title(self):
        """Update window title to show document name and modified status"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            title = f"{filename}{' *' if self.modified else ''}"
            self.title_label.set_text(title)
        else:
            self.title_label.set_text(f"Untitled{' *' if self.modified else ''}")
            
    def on_new_clicked(self, action, param):
        """Handle New command"""
        if self.modified:
            self.show_save_dialog_before_action(self.do_new_file)
        else:
            self.do_new_file()

    def do_new_file(self):
        """Create a new document"""
        js_code = "setContent('');"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        self.current_file = None
        self.modified = False
        self.update_window_title()
        self.status_label.set_text("New document created")

    def on_open_clicked(self, action, param):
        """Handle Open command"""
        if self.modified:
            self.show_save_dialog_before_action(self.do_open_file)
        else:
            self.do_open_file()

    def do_open_file(self):
        """Show open file dialog"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Document")
        
        filter_html = Gtk.FileFilter()
        filter_html.set_name("HTML files")
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")
        
        filter_txt = Gtk.FileFilter()
        filter_txt.set_name("Text files")
        filter_txt.add_pattern("*.txt")
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        
        # Create filters and set
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_html)
        filter_list.append(filter_txt)
        filter_list.append(filter_all)
        
        dialog.set_filters(filter_list)
        dialog.open(self.win, None, self.on_open_response)

    def on_open_response(self, dialog, result):
        """Handle open file dialog response with better error handling"""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                self.load_file(filepath)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark' or e.code != 2:
                self.show_error_dialog(f"Error opening file: {e}")

    def load_file(self, filepath):
        """Load file content into editor"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine if the content is HTML
            is_html = content.strip().startswith("<") and (
                "<html" in content.lower() or 
                "<body" in content.lower() or 
                "<div" in content.lower()
            )
            
            if is_html:
                # Extract body content if it's a full HTML document
                body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    content = body_match.group(1).strip()
            else:
                # Convert plain text to HTML
                content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                content = content.replace("\n", "<br>")
            
            # Set the content in the editor
            js_code = f"setContent(`{content.replace('`', '\\`')}`);"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            self.current_file = filepath
            self.modified = False
            self.update_window_title()
            self.status_label.set_text(f"Opened {os.path.basename(filepath)}")
            
            # Add to recent files
            self.add_to_recent_files(filepath)
            
        except Exception as e:
            self.show_error_dialog(f"Error loading file: {e}")
            
    def on_save_clicked(self, action, param):
        """Handle Save command"""
        if self.current_file:
            self.save_file(self.current_file)
        else:
            self.on_save_as_clicked(action, param)

    def on_save_as_clicked(self, action, param):
        """Handle Save As command"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Document")
        
        filter_html = Gtk.FileFilter()
        filter_html.set_name("HTML files")
        filter_html.add_pattern("*.html")
        
        filter_txt = Gtk.FileFilter()
        filter_txt.set_name("Text files")
        filter_txt.add_pattern("*.txt")
        
        # Create filters and set
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_html)
        filter_list.append(filter_txt)
        
        dialog.set_filters(filter_list)
        dialog.save(self.win, None, self.on_save_response)

    def on_save_response(self, dialog, result):
        """Handle save file dialog response with better error handling"""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                
                # Add extension if missing
                if not os.path.splitext(filepath)[1]:
                    filepath += ".html"
                
                self.save_file(filepath)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark' or e.code != 2:
                self.show_error_dialog(f"Error saving file: {e}")

    def save_file(self, filepath):
        """Save editor content to file"""
        js_code = "getContent();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, 
                                         lambda webview, result: self.on_get_content_for_save(
                                             webview, result, filepath))

    def on_get_content_for_save(self, webview, result, filepath):
        """Handle content retrieval for saving"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                content = js_result.to_string()
                
                # Check file extension to determine save format
                ext = os.path.splitext(filepath)[1].lower()
                
                if ext == '.txt':
                    # Convert HTML to plain text (simple approach)
                    plain_text = re.sub(r'<[^>]+>', '', content)
                    plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>')
                    plain_text = plain_text.replace('&amp;', '&').replace('&nbsp;', ' ')
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(plain_text)
                else:
                    # Save as HTML
                    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{os.path.basename(filepath)}</title>
</head>
<body>
{content}
</body>
</html>
"""
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_template)
                
                self.current_file = filepath
                self.modified = False
                self.update_window_title()
                self.status_label.set_text(f"Saved to {os.path.basename(filepath)}")
                
                # Add to recent files
                self.add_to_recent_files(filepath)
                
        except Exception as e:
            self.show_error_dialog(f"Error saving file: {e}")
    
    def on_print_clicked(self, action, param):
        """Handle Print command"""
        print_op = WebKit.PrintOperation.new(self.webview)
        print_op.run_dialog(self.win)

    def on_exit_clicked(self, action, param):
        """Handle Exit command"""
        if self.modified:
            self.show_save_dialog_before_action(lambda: self.win.destroy())
        else:
            self.win.destroy()

    def show_save_dialog_before_action(self, callback):
        """Show save confirmation dialog before proceeding with action"""
        
        # Create a dialog using the newer API
        dialog = Adw.Dialog.new()
        dialog.set_title("Save changes?")
        dialog.set_content_width(350)
        
        # Create a content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Question icon
        question_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        question_icon.set_pixel_size(48)
        question_icon.set_margin_bottom(12)
        content_box.append(question_icon)
        
        # Message
        message_label = Gtk.Label(label="Your document has unsaved changes. Do you want to save them?")
        message_label.set_wrap(True)
        message_label.set_max_width_chars(40)
        content_box.append(message_label)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)
        
        # Cancel button
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda btn: dialog.close())
        button_box.append(cancel_button)
        
        # Discard button
        discard_button = Gtk.Button(label="Discard")
        discard_button.add_css_class("destructive-action")
        discard_button.connect("clicked", lambda btn: self.on_save_dialog_discard(dialog, callback))
        button_box.append(discard_button)
        
        # Save button
        save_button = Gtk.Button(label="Save")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", lambda btn: self.on_save_dialog_save(dialog, callback))
        button_box.append(save_button)
        
        content_box.append(button_box)
        
        # Set the content and present
        dialog.set_child(content_box)  # Changed from set_content to set_child
        dialog.present(self.win)
        

    def on_save_dialog_save(self, dialog, callback):
        """Handle save button click in save dialog"""
        if self.current_file:
            self.save_file(self.current_file)
            self.modified = False
            dialog.close()
            callback()
        else:
            # Need to show Save As dialog
            dialog.close()
            
            save_dialog = Gtk.FileDialog()
            save_dialog.set_title("Save Document")
            
            filter_html = Gtk.FileFilter()
            filter_html.set_name("HTML files")
            filter_html.add_pattern("*.html")
            
            filter_txt = Gtk.FileFilter()
            filter_txt.set_name("Text files")
            filter_txt.add_pattern("*.txt")
            
            # Create filters and set
            filter_list = Gio.ListStore.new(Gtk.FileFilter)
            filter_list.append(filter_html)
            filter_list.append(filter_txt)
            
            save_dialog.set_filters(filter_list)
            save_dialog.save(self.win, None, 
                            lambda dialog, result: self.on_save_before_action_response(
                                dialog, result, callback))

    def on_save_dialog_discard(self, dialog, callback):
        """Handle discard button click in save dialog"""
        self.modified = False
        dialog.close()
        callback()       
         
    def on_save_before_action_response(self, dialog, result, callback):
        """Handle save file dialog response before executing another action with better error handling"""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                
                # Add extension if missing
                if not os.path.splitext(filepath)[1]:
                    filepath += ".html"
                
                self.save_file(filepath)
                self.modified = False
                callback()
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark' or e.code != 2:
                self.show_error_dialog(f"Error saving file: {e}")

    def show_error_dialog(self, message):
        """Show error message dialog using modern API"""
        
        # Create a dialog using the newer API
        dialog = Adw.Dialog.new()
        dialog.set_title("Error")
        dialog.set_content_width(350)
        
        # Create a content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Error icon
        error_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        error_icon.set_pixel_size(48)
        error_icon.set_margin_bottom(12)
        content_box.append(error_icon)
        
        # Error message
        message_label = Gtk.Label(label=message)
        message_label.set_wrap(True)
        message_label.set_max_width_chars(40)
        content_box.append(message_label)
        
        # OK button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)
        
        ok_button = Gtk.Button(label="OK")
        ok_button.add_css_class("suggested-action")
        ok_button.connect("clicked", lambda btn: dialog.close())
        button_box.append(ok_button)
        
        content_box.append(button_box)
        
        # Set the content and present
        dialog.set_child(content_box)  # Changed from set_content to set_child
        dialog.present(self.win)
        
    # Formatting command handlers

    def on_font_changed(self, button, param):
        """Handle font change with improved style application"""
        font_desc = button.get_font_desc()
        if font_desc:
            # Extract font properties
            family = font_desc.get_family()
            size = font_desc.get_size() / Pango.SCALE
            weight = font_desc.get_weight()
            style = font_desc.get_style()
            
            # Set font family
            js_code = f"setFontFamily('{family}');"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Set font size (convert Pango size to HTML size)
            html_size = min(7, max(1, int(size / 3)))
            js_code = f"setFontSize({html_size});"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Apply bold if font weight is sufficiently bold
            is_bold = weight >= Pango.Weight.BOLD
            js_code = """
            (function() {
                // Get current selection state
                let isBold = document.queryCommandState('bold');
                
                // Only toggle if different from current state
                if (isBold !== %s) {
                    document.execCommand('bold', false, null);
                }
                return true;
            })();
            """ % ('true' if is_bold else 'false')
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Update the bold button state without triggering the callback
            self.bold_button.handler_block_by_func(self.on_bold_toggled)
            self.bold_button.set_active(is_bold)
            self.bold_button.handler_unblock_by_func(self.on_bold_toggled)
            
            # Similar handling for italic
            is_italic = style == Pango.Style.ITALIC or style == Pango.Style.OBLIQUE
            js_code = """
            (function() {
                // Get current selection state
                let isItalic = document.queryCommandState('italic');
                
                // Only toggle if different from current state
                if (isItalic !== %s) {
                    document.execCommand('italic', false, null);
                }
                return true;
            })();
            """ % ('true' if is_italic else 'false')
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Update the italic button state
            self.italic_button.handler_block_by_func(self.on_italic_toggled)
            self.italic_button.set_active(is_italic)
            self.italic_button.handler_unblock_by_func(self.on_italic_toggled)

    def on_bold_toggled(self, button):
        """Handle bold button toggle"""
        js_code = "setBold();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_italic_toggled(self, button):
        """Handle italic button toggle"""
        js_code = "setItalic();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_underline_toggled(self, button):
        """Handle underline button toggle"""
        js_code = "setUnderline();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
    def on_strikethrough_toggled(self, button):
        """Handle strikethrough button toggle"""
        js_code = "setStrikethrough();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
    def on_superscript_toggled(self, button):
        """Handle superscript button toggle"""
        js_code = "setSuperscript();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        # Ensure subscript is turned off
        if button.get_active():
            self.subscript_button.handler_block_by_func(self.on_subscript_toggled)
            self.subscript_button.set_active(False)
            self.subscript_button.handler_unblock_by_func(self.on_subscript_toggled)
        
    def on_subscript_toggled(self, button):
        """Handle subscript button toggle"""
        js_code = "setSubscript();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        # Ensure superscript is turned off
        if button.get_active():
            self.superscript_button.handler_block_by_func(self.on_superscript_toggled)
            self.superscript_button.set_active(False)
            self.superscript_button.handler_unblock_by_func(self.on_superscript_toggled)

    def on_align_left_toggled(self, button):
        """Handle align left button toggle"""
        if button.get_active():
            js_code = "setAlignment('Left');"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Uncheck other alignment buttons
            self.align_center_button.handler_block_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_block_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_block_by_func(self.on_align_justify_toggled)
            
            self.align_center_button.set_active(False)
            self.align_right_button.set_active(False)
            self.align_justify_button.set_active(False)
            
            self.align_center_button.handler_unblock_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_unblock_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_unblock_by_func(self.on_align_justify_toggled)
            
    def on_align_center_toggled(self, button):
        """Handle align center button toggle"""
        if button.get_active():
            js_code = "setAlignment('Center');"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Uncheck other alignment buttons
            self.align_left_button.handler_block_by_func(self.on_align_left_toggled)
            self.align_right_button.handler_block_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_block_by_func(self.on_align_justify_toggled)
            
            self.align_left_button.set_active(False)
            self.align_right_button.set_active(False)
            self.align_justify_button.set_active(False)
            
            self.align_left_button.handler_unblock_by_func(self.on_align_left_toggled)
            self.align_right_button.handler_unblock_by_func(self.on_align_right_toggled)
            self.align_justify_button.handler_unblock_by_func(self.on_align_justify_toggled)

    def on_align_right_toggled(self, button):
        """Handle align right button toggle"""
        if button.get_active():
            js_code = "setAlignment('Right');"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Uncheck other alignment buttons
            self.align_left_button.handler_block_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_block_by_func(self.on_align_center_toggled)
            self.align_justify_button.handler_block_by_func(self.on_align_justify_toggled)
            
            self.align_left_button.set_active(False)
            self.align_center_button.set_active(False)
            self.align_justify_button.set_active(False)
            
            self.align_left_button.handler_unblock_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_unblock_by_func(self.on_align_center_toggled)
            self.align_justify_button.handler_unblock_by_func(self.on_align_justify_toggled)

    def on_align_justify_toggled(self, button):
        """Handle align justify button toggle"""
        if button.get_active():
            js_code = "setAlignment('Full');"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            
            # Uncheck other alignment buttons
            self.align_left_button.handler_block_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_block_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_block_by_func(self.on_align_right_toggled)
            
            self.align_left_button.set_active(False)
            self.align_center_button.set_active(False)
            self.align_right_button.set_active(False)
            
            self.align_left_button.handler_unblock_by_func(self.on_align_left_toggled)
            self.align_center_button.handler_unblock_by_func(self.on_align_center_toggled)
            self.align_right_button.handler_unblock_by_func(self.on_align_right_toggled)
            
    def on_text_color_changed(self, button):
        """Handle text color change"""
        # Use the RGBA property directly
        rgba = button.get_rgba()  # Still works but is deprecated
        
        # Alternative approach that's future-proof:
        # color = button.get_color()
        # rgba = Gdk.RGBA()
        # rgba.red = color.red / 65535.0
        # rgba.green = color.green / 65535.0
        # rgba.blue = color.blue / 65535.0
        # rgba.alpha = 1.0
        
        hex_color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        js_code = f"setTextColor('{hex_color}');"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    # Apply the same fix to the on_bg_color_changed method
    def on_bg_color_changed(self, button):
        """Handle background color change"""
        rgba = button.get_rgba()  # Still works but is deprecated
        
        # Alternative approach that's future-proof:
        # color = button.get_color()
        # rgba = Gdk.RGBA()
        # rgba.red = color.red / 65535.0
        # rgba.green = color.green / 65535.0
        # rgba.blue = color.blue / 65535.0
        # rgba.alpha = 1.0
        
        hex_color = f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"
        js_code = f"setBackgroundColor('{hex_color}');"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
    def on_bullet_list_toggled(self, button):
        """Handle bullet list button toggle"""
        js_code = "insertBulletList();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Uncheck numbered list button
        if button.get_active():
            self.numbered_list_button.handler_block_by_func(self.on_numbered_list_toggled)
            self.numbered_list_button.set_active(False)
            self.numbered_list_button.handler_unblock_by_func(self.on_numbered_list_toggled)

    def on_numbered_list_toggled(self, button):
        """Handle numbered list button toggle"""
        js_code = "insertNumberedList();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Uncheck bullet list button
        if button.get_active():
            self.bullet_list_button.handler_block_by_func(self.on_bullet_list_toggled)
            self.bullet_list_button.set_active(False)
            self.bullet_list_button.handler_unblock_by_func(self.on_bullet_list_toggled)

    def on_indent_clicked(self, button):
        """Handle indent button click"""
        js_code = "increaseIndent();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_outdent_clicked(self, button):
        """Handle outdent button click"""
        js_code = "decreaseIndent();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    # Keyboard shortcut handlers
    
    def on_bold_shortcut(self, action, param):
        """Handle Ctrl+B shortcut"""
        self.bold_button.set_active(not self.bold_button.get_active())
        
    def on_italic_shortcut(self, action, param):
        """Handle Ctrl+I shortcut"""
        self.italic_button.set_active(not self.italic_button.get_active())
        
    def on_underline_shortcut(self, action, param):
        """Handle Ctrl+U shortcut"""
        self.underline_button.set_active(not self.underline_button.get_active())
        
    def on_strikethrough_shortcut(self, action, param):
        """Handle Ctrl+K shortcut"""
        self.strikethrough_button.set_active(not self.strikethrough_button.get_active())
        
    def on_undo_clicked(self, action, param):
        """Handle Undo command using custom implementation with debug output"""
        js_code = """
        (function() {
            console.log("Python-triggered undo", editorHistory.length, historyIndex);
            debugHistory();
            return customUndo();
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, 
                                        lambda webview, result: self.handle_undo_result(webview, result))
        
    def handle_undo_result(self, webview, result):
        """Handle result from undo operation"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                success = js_result.to_boolean()
                if success:
                    self.status_label.set_text("Undo completed")
                else:
                    self.status_label.set_text("Nothing to undo")
        except Exception as e:
            print(f"Error handling undo result: {e}")
            self.status_label.set_text("Undo error")

    def on_redo_clicked(self, action, param):
        """Handle Redo command using custom implementation with debug output"""
        js_code = """
        (function() {
            console.log("Python-triggered redo", editorHistory.length, historyIndex);
            debugHistory();
            return customRedo();
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None,
                                        lambda webview, result: self.handle_redo_result(webview, result))

    def handle_redo_result(self, webview, result):
        """Handle result from redo operation"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                success = js_result.to_boolean()
                if success:
                    self.status_label.set_text("Redo completed")
                else:
                    self.status_label.set_text("Nothing to redo")
        except Exception as e:
            print(f"Error handling redo result: {e}")
            self.status_label.set_text("Redo error")
        
    # RTL support
    def on_rtl_toggled(self, button):
        """Handle RTL button toggle"""
        js_code = "toggleRTL();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, 
                                        lambda webview, result: self.on_rtl_toggled_result(
                                            webview, result, button))
        
    def on_rtl_toggled_result(self, webview, result, button):
        """Handle result of RTL toggle"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                is_rtl = js_result.to_boolean()
                if is_rtl:
                    self.status_label.set_text("Right-to-left mode enabled")
                else:
                    self.status_label.set_text("Left-to-right mode enabled")
        except Exception as e:
            print(f"Error toggling RTL: {e}")
    
    def on_toggle_rtl(self, action, param):
        """Handle keyboard shortcut for RTL toggle"""
        self.rtl_button.set_active(not self.rtl_button.get_active())
    
    # Date and time insertion
    def on_insert_datetime_clicked(self, action, param):
        """Show enhanced dialog to select date/time format with three-column layout in a scrolled window"""
        dialog = Adw.Dialog()
        dialog.set_title("Insert Date Time")
        
        # Create main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Get current date and time for preview
        now = datetime.datetime.now()
        
        # Create a scrolled window to contain the grid
        scrolled_window = Gtk.ScrolledWindow()
        # Set dimensions to show at least 4 items vertically without scrolling
        scrolled_window.set_min_content_height(300)
        # Width to ensure all 3 columns are clearly visible
        scrolled_window.set_min_content_width(600)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        
        # Create a grid layout for the three columns
        format_grid = Gtk.Grid()
        format_grid.set_row_spacing(6)
        format_grid.set_column_spacing(6)
        format_grid.set_column_homogeneous(True)
        format_grid.set_margin_top(6)
        format_grid.set_margin_bottom(6)
        format_grid.set_margin_start(6)
        format_grid.set_margin_end(6)
        
        # Create headers for each column
        date_header = Gtk.Label()
        date_header.set_markup("<b>Date</b>")
        date_header.set_halign(Gtk.Align.CENTER)
        date_header.add_css_class("title-4")
        date_header.set_margin_bottom(6)
        
        time_header = Gtk.Label()
        time_header.set_markup("<b>Time</b>")
        time_header.set_halign(Gtk.Align.CENTER)
        time_header.add_css_class("title-4")
        time_header.set_margin_bottom(6)
        
        datetime_header = Gtk.Label()
        datetime_header.set_markup("<b>Date &amp; Time</b>")
        datetime_header.set_halign(Gtk.Align.CENTER)
        datetime_header.add_css_class("title-4")
        datetime_header.set_margin_bottom(6)
        
        # Add headers to the grid
        format_grid.attach(date_header, 0, 0, 1, 1)
        format_grid.attach(time_header, 1, 0, 1, 1)
        format_grid.attach(datetime_header, 2, 0, 1, 1)
        
        # Define format options
        date_formats = [
            {"name": "Short", "format": now.strftime("%m/%d/%Y"), "type": "date_short"},
            {"name": "Medium", "format": now.strftime("%b %d, %Y"), "type": "date_medium"},
            {"name": "Long", "format": now.strftime("%B %d, %Y"), "type": "date_long"},
            {"name": "Full", "format": now.strftime("%A, %B %d, %Y"), "type": "date_full"},
            {"name": "ISO", "format": now.strftime("%Y-%m-%d"), "type": "date_iso"},
            {"name": "European", "format": now.strftime("%d/%m/%Y"), "type": "date_euro"},
        ]
        
        time_formats = [
            {"name": "12-hour", "format": now.strftime("%I:%M %p"), "type": "time_12"},
            {"name": "24-hour", "format": now.strftime("%H:%M"), "type": "time_24"},
            {"name": "12h with seconds", "format": now.strftime("%I:%M:%S %p"), "type": "time_12_sec"},
            {"name": "24h with seconds", "format": now.strftime("%H:%M:%S"), "type": "time_24_sec"},
        ]
        
        datetime_formats = [
            {"name": "Short", "format": now.strftime("%m/%d/%Y %I:%M %p"), "type": "datetime_short"},
            {"name": "Medium", "format": now.strftime("%b %d, %Y %H:%M"), "type": "datetime_medium"},
            {"name": "Long", "format": now.strftime("%B %d, %Y at %I:%M %p"), "type": "datetime_long"},
            {"name": "ISO", "format": now.strftime("%Y-%m-%d %H:%M:%S"), "type": "datetime_iso"},
            {"name": "RFC", "format": now.strftime("%a, %d %b %Y %H:%M:%S"), "type": "datetime_rfc"},
        ]
        
        # Store all format buttons to access the selected one later
        self.format_buttons = []
        
        # Create Date format buttons (column 0)
        for i, fmt in enumerate(date_formats):
            button = Gtk.ToggleButton(label=fmt["name"])
            button.format_type = fmt["type"]
            button.format_value = fmt["format"]
            
            # Add tooltip showing the format preview
            button.set_tooltip_text(fmt["format"])
            
            # Add to button group for radio button behavior
            if self.format_buttons:
                button.set_group(self.format_buttons[0])
            
            self.format_buttons.append(button)
            
            # Create a box to arrange the button and preview
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(2)
            box.set_margin_bottom(2)
            
            # Make button wider to better display text
            button.set_hexpand(True)
            button.set_size_request(-1, 36)  # Width: default, Height: 36px
            box.append(button)
            
            # Add small preview label
            preview = Gtk.Label(label=fmt["format"])
            preview.add_css_class("caption")
            preview.add_css_class("dim-label")
            preview.set_margin_top(2)
            box.append(preview)
            
            # Add to grid
            format_grid.attach(box, 0, i+1, 1, 1)
        
        # Create Time format buttons (column 1)
        for i, fmt in enumerate(time_formats):
            button = Gtk.ToggleButton(label=fmt["name"])
            button.format_type = fmt["type"]
            button.format_value = fmt["format"]
            
            # Add tooltip
            button.set_tooltip_text(fmt["format"])
            
            # Add to button group
            button.set_group(self.format_buttons[0])
            self.format_buttons.append(button)
            
            # Create a box to arrange the button and preview
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.append(button)
            
            # Add small preview label
            preview = Gtk.Label(label=fmt["format"])
            preview.add_css_class("caption")
            preview.add_css_class("dim-label")
            box.append(preview)
            
            # Add to grid
            format_grid.attach(box, 1, i+1, 1, 1)
        
        # No need for placeholders since we now have exactly 4 items in each category
        
        # Create Date & Time format buttons (column 2)
        for i, fmt in enumerate(datetime_formats):
            button = Gtk.ToggleButton(label=fmt["name"])
            button.format_type = fmt["type"]
            button.format_value = fmt["format"]
            
            # Add tooltip
            button.set_tooltip_text(fmt["format"])
            
            # Add to button group
            button.set_group(self.format_buttons[0])
            self.format_buttons.append(button)
            
            # Create a box to arrange the button and preview
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.append(button)
            
            # Add small preview label
            preview = Gtk.Label(label=fmt["format"])
            preview.add_css_class("caption")
            preview.add_css_class("dim-label")
            box.append(preview)
            
            # Add to grid
            format_grid.attach(box, 2, i+1, 1, 1)
        
        # Add grid to scrolled window
        scrolled_window.set_child(format_grid)
        
        # Add scrolled window to content box
        content_box.append(scrolled_window)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(4)
        
        # Cancel button
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda btn: dialog.force_close())
        button_box.append(cancel_button)
        
        # Insert button
        insert_button = Gtk.Button(label="Insert")
        insert_button.add_css_class("suggested-action")
        insert_button.connect("clicked", lambda btn: self.insert_selected_datetime_format(dialog))
        button_box.append(insert_button)
        
        content_box.append(button_box)
        
        # Create a clamp to hold the content
        clamp = Adw.Clamp()
        clamp.set_child(content_box)
        
        # Set up the dialog content using a box
        dialog_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog_content.append(clamp)
        
        # Connect the content to the dialog
        dialog.connect("closed", lambda d: None)  # Ensure proper cleanup
        dialog.set_child(dialog_content)
        
        # Present the dialog
        dialog.present(self.win)

    def insert_selected_datetime_format(self, dialog):
        """Insert date/time with the selected format"""
        # Check if any format button is selected
        selected_button = None
        for button in self.format_buttons:
            if button.get_active():
                selected_button = button
                break
        
        if selected_button:
            # Get the pre-formatted value directly from the button
            formatted_date = selected_button.format_value
            
            # Insert the formatted date at the current cursor position
            js_code = f"""
            (function() {{
                document.execCommand('insertText', false, `{formatted_date}`);
                return true;
            }})();
            """
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
            dialog.force_close()
        else:
            # No selection - show a message
            self.show_error_dialog("Please select a date/time format")
        
    # Paragraph spacing
    def on_paragraph_spacing_clicked(self, action, param):
        """Show dialog to adjust paragraph spacing for individual or all paragraphs"""
        dialog = Adw.Dialog()
        dialog.set_title("Paragraph Spacing")
        
        # Create main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Create spacing selection
        header = Gtk.Label()
        header.set_markup("<b>Paragraph Spacing Options:</b>")
        header.set_halign(Gtk.Align.START)
        content_box.append(header)
        
        # Radio buttons for scope selection
        scope_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scope_box.set_margin_top(12)
        scope_box.set_margin_bottom(12)
        
        scope_label = Gtk.Label(label="Apply to:")
        scope_label.set_halign(Gtk.Align.START)
        scope_box.append(scope_label)
        
        # Create radio buttons
        current_radio = Gtk.CheckButton(label="Current paragraph only")
        current_radio.set_active(True)
        scope_box.append(current_radio)
        
        all_radio = Gtk.CheckButton(label="All paragraphs")
        all_radio.set_group(current_radio)
        scope_box.append(all_radio)
        
        content_box.append(scope_box)
        
        # Spacing slider
        spacing_label = Gtk.Label(label="Spacing value:")
        spacing_label.set_halign(Gtk.Align.START)
        content_box.append(spacing_label)
        
        adjustment = Gtk.Adjustment.new(10, 0, 50, 1, 5, 0)
        spacing_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        spacing_scale.set_hexpand(True)
        spacing_scale.set_digits(0)
        spacing_scale.set_draw_value(True)
        spacing_scale.add_mark(0, Gtk.PositionType.BOTTOM, "None")
        spacing_scale.add_mark(10, Gtk.PositionType.BOTTOM, "Default")
        spacing_scale.add_mark(30, Gtk.PositionType.BOTTOM, "Wide")
        content_box.append(spacing_scale)
        
        # Preset buttons
        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        presets_box.set_homogeneous(True)
        presets_box.set_margin_top(12)
        
        none_button = Gtk.Button(label="None")
        none_button.connect("clicked", lambda btn: spacing_scale.set_value(0))
        presets_box.append(none_button)
        
        small_button = Gtk.Button(label="Small")
        small_button.connect("clicked", lambda btn: spacing_scale.set_value(5))
        presets_box.append(small_button)
        
        medium_button = Gtk.Button(label="Medium") 
        medium_button.connect("clicked", lambda btn: spacing_scale.set_value(15))
        presets_box.append(medium_button)
        
        large_button = Gtk.Button(label="Large")
        large_button.connect("clicked", lambda btn: spacing_scale.set_value(30))
        presets_box.append(large_button)
        
        content_box.append(presets_box)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)
        
        # Cancel button
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda btn: dialog.force_close())
        button_box.append(cancel_button)
        
        # Apply button
        apply_button = Gtk.Button(label="Apply")
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", lambda btn: self.apply_paragraph_spacing(
            dialog, spacing_scale.get_value(), current_radio.get_active()))
        button_box.append(apply_button)
        
        content_box.append(button_box)
        
        # Create a clamp to hold the content
        clamp = Adw.Clamp()
        clamp.set_child(content_box)
        
        # Set up the dialog content
        dialog_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog_content.append(clamp)
        
        # Connect the content to the dialog
        dialog.connect("closed", lambda d: None)  # Ensure proper cleanup
        dialog.set_child(dialog_content)
        
        # Present the dialog
        dialog.present(self.win)

    def apply_paragraph_spacing(self, dialog, spacing, current_only):
        """Apply paragraph spacing to the current paragraph or all paragraphs"""
        if current_only:
            # Apply spacing to the current paragraph only
            js_code = f"setParagraphSpacing({int(spacing)});"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        else:
            # Apply spacing to all paragraphs
            js_code = f"""
            (function() {{
                // First ensure all direct text content is wrapped
                wrapUnwrappedText(document.getElementById('editor'));
                
                // Target both p tags and div tags as paragraphs
                let paragraphs = document.getElementById('editor').querySelectorAll('p, div');
                
                // Apply to all paragraphs
                for (let i = 0; i < paragraphs.length; i++) {{
                    paragraphs[i].style.marginBottom = {int(spacing)} + 'px';
                }}
                
                return true;
            }})();
            """
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        dialog.force_close()

    def on_context_menu(self, web_view, context_menu, event, hit_test_result):
        """Handle context menu creation for the editor"""
        # Add paragraph spacing submenu
        spacing_menu = context_menu.append_new_submenu(WebKit.ContextMenuItem.new_with_label("Paragraph Spacing"))
        
        # Add spacing options
        none_item = WebKit.ContextMenuItem.new_with_label("None")
        none_item.connect("activate", lambda item: self.apply_quick_paragraph_spacing(0))
        spacing_menu.append(none_item)
        
        small_item = WebKit.ContextMenuItem.new_with_label("Small (5px)")
        small_item.connect("activate", lambda item: self.apply_quick_paragraph_spacing(5))
        spacing_menu.append(small_item)
        
        medium_item = WebKit.ContextMenuItem.new_with_label("Medium (15px)")
        medium_item.connect("activate", lambda item: self.apply_quick_paragraph_spacing(15))
        spacing_menu.append(medium_item)
        
        large_item = WebKit.ContextMenuItem.new_with_label("Large (30px)")
        large_item.connect("activate", lambda item: self.apply_quick_paragraph_spacing(30))
        spacing_menu.append(large_item)
        
        # Add separator
        spacing_menu.append(WebKit.ContextMenuItem.new_separator())
        
        # Add custom spacing option
        custom_item = WebKit.ContextMenuItem.new_with_label("Custom...")
        custom_item.connect("activate", lambda item: self.on_paragraph_spacing_clicked(None, None))
        spacing_menu.append(custom_item)
        
        # Add line spacing submenu
        line_spacing_menu = context_menu.append_new_submenu(WebKit.ContextMenuItem.new_with_label("Line Spacing"))
        
        # Add line spacing options
        single_item = WebKit.ContextMenuItem.new_with_label("Single (1.0)")
        single_item.connect("activate", lambda item: self.apply_quick_line_spacing(1.0))
        line_spacing_menu.append(single_item)
        
        one_half_item = WebKit.ContextMenuItem.new_with_label("1.5 lines")
        one_half_item.connect("activate", lambda item: self.apply_quick_line_spacing(1.5))
        line_spacing_menu.append(one_half_item)
        
        double_item = WebKit.ContextMenuItem.new_with_label("Double (2.0)")
        double_item.connect("activate", lambda item: self.apply_quick_line_spacing(2.0))
        line_spacing_menu.append(double_item)
        
        # Add separator
        line_spacing_menu.append(WebKit.ContextMenuItem.new_separator())
        
        # Add custom spacing option
        custom_item = WebKit.ContextMenuItem.new_with_label("Custom...")
        custom_item.connect("activate", lambda item: self.on_line_spacing_clicked(None, None))
        line_spacing_menu.append(custom_item)
        
        # Allow the context menu to show
        return False

    def apply_quick_paragraph_spacing(self, spacing):
        """Apply spacing to the current paragraph through context menu"""
        js_code = f"setParagraphSpacing({spacing});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
    
    # Line spacing
    def on_line_spacing_clicked(self, action, param):
        """Show dialog to adjust line spacing for individual or all paragraphs"""
        dialog = Adw.Dialog()
        dialog.set_title("Line Spacing")
        
        # Create main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Create spacing selection
        header = Gtk.Label()
        header.set_markup("<b>Line Spacing Options:</b>")
        header.set_halign(Gtk.Align.START)
        content_box.append(header)
        
        # Radio buttons for scope selection
        scope_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scope_box.set_margin_top(12)
        scope_box.set_margin_bottom(12)
        
        scope_label = Gtk.Label(label="Apply to:")
        scope_label.set_halign(Gtk.Align.START)
        scope_box.append(scope_label)
        
        # Create radio buttons
        current_radio = Gtk.CheckButton(label="Current paragraph only")
        current_radio.set_active(True)
        scope_box.append(current_radio)
        
        all_radio = Gtk.CheckButton(label="All paragraphs")
        all_radio.set_group(current_radio)
        scope_box.append(all_radio)
        
        content_box.append(scope_box)
        
        # Preset buttons
        presets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        presets_label = Gtk.Label(label="Common spacing:")
        presets_label.set_halign(Gtk.Align.START)
        presets_box.append(presets_label)
        
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons_box.set_homogeneous(True)
        
        single_button = Gtk.Button(label="Single (1.0)")
        single_button.connect("clicked", lambda btn: self.apply_line_spacing(
            dialog, 1.0, current_radio.get_active()))
        buttons_box.append(single_button)
        
        one_half_button = Gtk.Button(label="1.5 lines")
        one_half_button.connect("clicked", lambda btn: self.apply_line_spacing(
            dialog, 1.5, current_radio.get_active()))
        buttons_box.append(one_half_button)
        
        double_button = Gtk.Button(label="Double (2.0)")
        double_button.connect("clicked", lambda btn: self.apply_line_spacing(
            dialog, 2.0, current_radio.get_active()))
        buttons_box.append(double_button)
        
        presets_box.append(buttons_box)
        content_box.append(presets_box)
        
        # Custom spacing section
        custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        custom_box.set_margin_top(8)
        
        custom_label = Gtk.Label(label="Custom spacing:")
        custom_label.set_halign(Gtk.Align.START)
        custom_box.append(custom_label)
        
        # Add slider for custom spacing
        adjustment = Gtk.Adjustment.new(1.0, 0.8, 3.0, 0.1, 0.2, 0)
        spacing_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        spacing_scale.set_hexpand(True)
        spacing_scale.set_digits(1)
        spacing_scale.set_draw_value(True)
        spacing_scale.add_mark(1.0, Gtk.PositionType.BOTTOM, "1.0")
        spacing_scale.add_mark(1.5, Gtk.PositionType.BOTTOM, "1.5")
        spacing_scale.add_mark(2.0, Gtk.PositionType.BOTTOM, "2.0")
        custom_box.append(spacing_scale)
        
        # Apply custom button
        custom_apply_button = Gtk.Button(label="Apply Custom Value")
        custom_apply_button.connect("clicked", lambda btn: self.apply_line_spacing(
            dialog, spacing_scale.get_value(), current_radio.get_active()))
        custom_apply_button.set_margin_top(8)
        custom_box.append(custom_apply_button)
        
        content_box.append(custom_box)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)
        
        # Cancel button
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda btn: dialog.force_close())
        button_box.append(cancel_button)
        
        content_box.append(button_box)
        
        # Create a clamp to hold the content
        clamp = Adw.Clamp()
        clamp.set_child(content_box)
        
        # Set up the dialog content
        dialog_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog_content.append(clamp)
        
        # Connect the content to the dialog
        dialog.connect("closed", lambda d: None)  # Ensure proper cleanup
        dialog.set_child(dialog_content)
        
        # Present the dialog
        dialog.present(self.win)

    def apply_line_spacing(self, dialog, spacing, current_only):
        """Apply line spacing to the current paragraph or all paragraphs"""
        if current_only:
            # Apply spacing to the current paragraph only
            js_code = f"setLineSpacing({spacing});"
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        else:
            # Apply spacing to all paragraphs
            js_code = f"""
            (function() {{
                // First ensure all direct text content is wrapped
                wrapUnwrappedText(document.getElementById('editor'));
                
                // Target both p tags and div tags as paragraphs
                let paragraphs = document.getElementById('editor').querySelectorAll('p, div');
                
                // Apply to all paragraphs
                for (let i = 0; i < paragraphs.length; i++) {{
                    paragraphs[i].style.lineHeight = {spacing};
                }}
                
                return true;
            }})();
            """
            self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        dialog.force_close()

    def apply_quick_line_spacing(self, spacing):
        """Apply line spacing to the current paragraph through context menu"""
        js_code = f"setLineSpacing({spacing});"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

       
    # Recent files management
    def load_recent_files(self):
        """Load recent files from settings"""
        # In a real app, you would load from GSettings or a config file
        # For this example, we'll just use an empty list initially
        self.update_recent_files_menu()
    
    def update_recent_files_menu(self):
        """Update the recent files menu"""
        # Clear existing items
        while self.recent_menu.get_n_items() > 0:
            self.recent_menu.remove(0)
        
        # Add recent files to menu
        for i, filepath in enumerate(self.recent_files):
            filename = os.path.basename(filepath)
            action_name = f"recent_{i}"
            
            # Create action for this file
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", lambda a, p, path=filepath: self.open_recent_file(path))
            self.add_action(action)
            
            # Add menu item
            self.recent_menu.append(filename, f"app.{action_name}")
        
        # Add a "Clear Recent Files" option if there are files
        if self.recent_files:
            self.recent_menu.append("───────────", None)
            self.create_action("clear_recent", self.on_clear_recent_clicked)
            self.recent_menu.append("Clear Recent Files", "app.clear_recent")
    
    def add_to_recent_files(self, filepath):
        """Add a file to the recent files list"""
        # Remove if already exists
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        # Add to beginning of list
        self.recent_files.insert(0, filepath)
        
        # Limit to max number of recent files
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
        
        # Update menu
        self.update_recent_files_menu()
    
    def open_recent_file(self, filepath):
        """Open a file from the recent files list"""
        if os.path.exists(filepath):
            if self.modified:
                self.show_save_dialog_before_action(lambda: self.load_file(filepath))
            else:
                self.load_file(filepath)
        else:
            # File no longer exists
            self.show_error_dialog(f"File no longer exists: {filepath}")
            self.recent_files.remove(filepath)
            self.update_recent_files_menu()
    
    def on_clear_recent_clicked(self, action, param):
        """Clear the recent files list"""
        self.recent_files = []
        self.update_recent_files_menu()
        
    # Advanced Features
    def initialize_extras(self):
        """Initialize extra features"""
        # Add find and replace
        self.add_find_replace_functionality()
        
        # Add table toolbar
        self.create_table_toolbar()
        
        # Add table and image actions
        self.create_action("insert_table", self.on_insert_table_clicked)
        self.create_action("insert_image", self.on_insert_image_clicked)

    def add_find_replace_functionality(self):
        """Add find and replace functionality to the editor using Gtk.SearchEntry"""
        # Create a modern search bar
        self.find_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.find_bar.set_margin_start(10)
        self.find_bar.set_margin_end(10)
        self.find_bar.set_margin_top(5)
        self.find_bar.set_margin_bottom(5)
        self.find_bar.add_css_class("search-bar")
        
        # Use Gtk.SearchEntry for find functionality
        self.find_entry = Gtk.SearchEntry()
        self.find_entry.set_placeholder_text("Search")
        self.find_entry.set_tooltip_text("Find text in document")
        self.find_entry.set_hexpand(True)
        self.find_entry.connect("search-changed", self.on_find_text_changed)
        self.find_entry.connect("activate", self.on_find_next_clicked)
        
        # Add key controller specifically for the search entry
        find_key_controller = Gtk.EventControllerKey.new()
        find_key_controller.connect("key-pressed", self.on_find_key_pressed)
        self.find_entry.add_controller(find_key_controller)
        
        self.find_bar.append(self.find_entry)
        
        # Previous/Next buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        nav_box.add_css_class("linked")
        nav_box.set_margin_start(4)
        
        self.prev_button = Gtk.Button(icon_name="go-up-symbolic")
        self.prev_button.set_tooltip_text("Previous match")
        self.prev_button.connect("clicked", self.on_find_previous_clicked)
        nav_box.append(self.prev_button)
        
        self.next_button = Gtk.Button(icon_name="go-down-symbolic")
        self.next_button.set_tooltip_text("Next match")
        self.next_button.connect("clicked", self.on_find_next_clicked)
        nav_box.append(self.next_button)
        
        self.find_bar.append(nav_box)
        
        # Create a separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.set_margin_start(8)
        separator.set_margin_end(8)
        self.find_bar.append(separator)
        
        # Replace entry with icon
        replace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        replace_box.add_css_class("linked")
        
        # Create a styled entry for replace
        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace")
        self.replace_entry.set_hexpand(True)
        
        # Add a replace icon to the entry
        self.replace_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "edit-find-replace-symbolic")
        
        # Add key controller specifically for the replace entry
        replace_key_controller = Gtk.EventControllerKey.new()
        replace_key_controller.connect("key-pressed", self.on_find_key_pressed)
        self.replace_entry.add_controller(replace_key_controller)
        
        replace_box.append(self.replace_entry)
        self.find_bar.append(replace_box)
        
        # Replace and Replace All buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        action_box.set_margin_start(4)
        
        self.replace_button = Gtk.Button(label="Replace")
        self.replace_button.connect("clicked", self.on_replace_clicked)
        action_box.append(self.replace_button)
        
        self.replace_all_button = Gtk.Button(label="Replace All")
        self.replace_all_button.connect("clicked", self.on_replace_all_clicked)
        action_box.append(self.replace_all_button)
        
        self.find_bar.append(action_box)
        
        # Use a spacer to push the close button to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.find_bar.append(spacer)
        
        # Close button
        self.close_find_button = Gtk.Button(icon_name="window-close-symbolic")
        self.close_find_button.set_tooltip_text("Close search bar")
        self.close_find_button.connect("clicked", self.on_close_find_clicked)
        self.find_bar.append(self.close_find_button)
        
        # Add find bar to main box but initially hidden
        self.main_box.append(self.find_bar)
        self.find_bar.set_visible(False)
        
        # Also add a keyboard shortcut for Escape at the window level
        self.create_action("close_find", self.on_close_find_clicked, ["Escape"])
        
    def on_find_key_pressed(self, controller, keyval, keycode, state):
        """Handle key presses in the find bar"""
        # Check if Escape key was pressed
        if keyval == Gdk.KEY_Escape:
            self.on_close_find_clicked(None)
            return True
        return False

    def on_find_clicked(self, action, param):
        """Handle Find command"""
        self.find_bar.set_visible(True)
        self.find_entry.grab_focus()
    
    def on_close_find_clicked(self, button, param=None):
        """Handle close find bar button"""
        self.find_bar.set_visible(False)
        # Clear any highlighting
        js_code = "clearSearch();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
    def on_find_text_changed(self, entry):
        """Handle find text changes"""
        search_text = entry.get_text()
        if search_text:
            js_code = f"""
            searchAndHighlight("{search_text.replace('"', '\\"')}");
            """
            self.webview.evaluate_javascript(js_code, -1, None, None, None, 
                                            lambda webview, result: self.on_search_result(webview, result))

    def on_search_result(self, webview, result):
        """Handle search result"""
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result and not js_result.is_null():
                count = js_result.to_int32()
                if count > 0:
                    self.status_label.set_text(f"Found {count} matches")
                else:
                    self.status_label.set_text("No matches found")
        except Exception as e:
            print(f"Error in search: {e}")
            self.status_label.set_text("Search error")

    def on_find_next_clicked(self, button):
        """Move to next search result"""
        js_code = "findNext();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_find_previous_clicked(self, button):
        """Move to previous search result"""
        js_code = "findPrevious();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_replace_clicked(self, button):
        """Replace current selection with replace text"""
        replace_text = self.replace_entry.get_text()
        js_code = f"""
        replaceSelection("{replace_text.replace('"', '\\"')}");
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_replace_all_clicked(self, button):
        """Replace all instances of search text with replace text"""
        search_text = self.find_entry.get_text()
        replace_text = self.replace_entry.get_text()
        
        if not search_text:
            return
        
        js_code = f"""
        replaceAll("{search_text.replace('"', '\\"')}", "{replace_text.replace('"', '\\"')}");
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, 
                                        lambda webview, result: self.on_replace_all_result(webview, result))

    def on_replace_all_result(self, webview, result):
       """Handle replace all result"""
       try:
           js_result = webview.evaluate_javascript_finish(result)
           if js_result and not js_result.is_null():
               count = js_result.to_int32()
               self.status_label.set_text(f"Replaced {count} occurrences")
       except Exception as e:
           print(f"Error in replace all: {e}")
           self.status_label.set_text("Replace error")

    def on_insert_table_clicked(self, action, param):
       """Show dialog to insert table using modern Adw.Dialog API"""
       # Create a dialog using the newer API
       dialog = Adw.Dialog()
       dialog.set_title("Insert Table")
       
       # Create main content box
       content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
       content_box.set_margin_top(24)
       content_box.set_margin_bottom(24)
       content_box.set_margin_start(24)
       content_box.set_margin_end(24)
       
       # Add a header label
       header = Gtk.Label()
       header.set_markup("<b>Choose table dimensions</b>")
       header.set_halign(Gtk.Align.START)
       content_box.append(header)
       
       # Create settings grid
       settings_grid = Gtk.Grid()
       settings_grid.set_column_spacing(12)
       settings_grid.set_row_spacing(12)
       
       # Add row settings
       row_label = Gtk.Label(label="Rows:")
       row_label.set_halign(Gtk.Align.START)
       settings_grid.attach(row_label, 0, 0, 1, 1)
       
       row_adjustment = Gtk.Adjustment.new(3, 1, 20, 1, 5, 0)
       row_spinner = Gtk.SpinButton()
       row_spinner.set_adjustment(row_adjustment)
       settings_grid.attach(row_spinner, 1, 0, 1, 1)
       
       # Add column settings
       col_label = Gtk.Label(label="Columns:")
       col_label.set_halign(Gtk.Align.START)
       settings_grid.attach(col_label, 0, 1, 1, 1)
       
       col_adjustment = Gtk.Adjustment.new(3, 1, 10, 1, 5, 0)
       col_spinner = Gtk.SpinButton()
       col_spinner.set_adjustment(col_adjustment)
       settings_grid.attach(col_spinner, 1, 1, 1, 1)
       
       content_box.append(settings_grid)
       
       # Button box
       button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
       button_box.set_halign(Gtk.Align.END)
       button_box.set_margin_top(12)
       
       # Cancel button
       cancel_button = Gtk.Button(label="Cancel")
       cancel_button.connect("clicked", lambda btn: dialog.force_close())
       button_box.append(cancel_button)
       
       # Insert button
       insert_button = Gtk.Button(label="Insert")
       insert_button.add_css_class("suggested-action")
       insert_button.connect("clicked", lambda btn: self.on_insert_table_dialog_response(
           dialog, row_spinner.get_value_as_int(), col_spinner.get_value_as_int()))
       button_box.append(insert_button)
       
       content_box.append(button_box)
       
       # Create a clamp to hold the content
       clamp = Adw.Clamp()
       clamp.set_child(content_box)
       
       # Set up the dialog content using a box
       dialog_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
       dialog_content.append(clamp)
       
       # Connect the content to the dialog
       dialog.connect("closed", lambda d: None)  # Ensure proper cleanup
       dialog.set_child(dialog_content)
       
       # Present the dialog
       dialog.present(self.win)

    def on_insert_image_clicked(self, action, param):
        """Show dialog to insert image"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Image")
        
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Image files")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/gif")
        filter_img.add_mime_type("image/svg+xml")
        
        # Create filters and set
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_img)
        
        dialog.set_filters(filter_list)
        dialog.open(self.win, None, self.on_image_selected)
    
    def on_image_selected(self, dialog, result):
        """Handle image file selection with better error handling"""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                
                # For simplicity, we'll use a data URL to embed the image
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type:
                    mime_type = 'image/png'  # Default to png
                
                data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('utf-8')}"
                
                # Insert image at current cursor position
                js_code = f"""
                (function() {{
                    document.execCommand('insertImage', false, '{data_url}');
                    return true;
                }})();
                """
                self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark' or e.code != 2:
                self.show_error_dialog(f"Error inserting image: {e}")
        except Exception as e:
            # Handle other non-dialog errors
            self.show_error_dialog(f"Error inserting image: {e}")

    #  Table toolbar
    def on_table_clicked(self, manager, message):
        """Handle table click event from editor"""
        self.show_table_toolbar()
        self.status_label.set_text("Table selected")
        
    def create_table_toolbar(self):
        """Create a toolbar for table editing with enhanced features and symbolic icons"""
        self.table_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.table_toolbar.set_margin_start(10)
        self.table_toolbar.set_margin_end(10)
        self.table_toolbar.set_margin_top(5)
        self.table_toolbar.set_margin_bottom(5)
        
        # Table operations label
        table_label = Gtk.Label(label="Table:")
        table_label.set_margin_end(10)
        self.table_toolbar.append(table_label)
        
        # Add Row Above button
        add_row_above_button = Gtk.Button(icon_name="table-add-row-above-symbolic")
        add_row_above_button.set_tooltip_text("Add row above")
        add_row_above_button.connect("clicked", self.on_add_row_above_clicked)
        self.table_toolbar.append(add_row_above_button)
        
        # Add Row Below button
        add_row_below_button = Gtk.Button(icon_name="table-add-row-below-symbolic")
        add_row_below_button.set_tooltip_text("Add row below")
        add_row_below_button.connect("clicked", self.on_add_row_below_clicked)
        self.table_toolbar.append(add_row_below_button)
        
        # Add Column Before button
        add_col_before_button = Gtk.Button(icon_name="table-add-column-before-symbolic")
        add_col_before_button.set_tooltip_text("Add column before")
        add_col_before_button.connect("clicked", self.on_add_column_before_clicked)
        self.table_toolbar.append(add_col_before_button)
        
        # Add Column After button
        add_col_after_button = Gtk.Button(icon_name="table-add-column-after-symbolic")
        add_col_after_button.set_tooltip_text("Add column after")
        add_col_after_button.connect("clicked", self.on_add_column_after_clicked)
        self.table_toolbar.append(add_col_after_button)
        
        # Small separator
        separator1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator1.set_margin_start(5)
        separator1.set_margin_end(5)
        self.table_toolbar.append(separator1)
        
        # Delete Row button
        del_row_button = Gtk.Button(icon_name="table-delete-row-symbolic")
        del_row_button.set_tooltip_text("Delete row")
        del_row_button.connect("clicked", self.on_delete_row_clicked)
        self.table_toolbar.append(del_row_button)
        
        # Delete Column button
        del_col_button = Gtk.Button(icon_name="table-delete-column-symbolic")
        del_col_button.set_tooltip_text("Delete column")
        del_col_button.connect("clicked", self.on_delete_column_clicked)
        self.table_toolbar.append(del_col_button)
        
        # Delete Table button
        del_table_button = Gtk.Button(icon_name="table-delete-symbolic")
        del_table_button.set_tooltip_text("Delete table")
        del_table_button.connect("clicked", self.on_delete_table_clicked)
        self.table_toolbar.append(del_table_button)
        
        # Separator
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator2.set_margin_start(10)
        separator2.set_margin_end(10)
        self.table_toolbar.append(separator2)
        
        # Alignment options
        align_label = Gtk.Label(label="Align:")
        align_label.set_margin_end(5)
        self.table_toolbar.append(align_label)
        
        # Left alignment
        align_left_button = Gtk.Button(icon_name="table-align-left-symbolic")
        align_left_button.set_tooltip_text("Align Left (text wraps around right)")
        align_left_button.connect("clicked", self.on_table_align_left)
        self.table_toolbar.append(align_left_button)
        
        # Center alignment
        align_center_button = Gtk.Button(icon_name="table-align-horizontal-centre-symbolic")
        align_center_button.set_tooltip_text("Center (no text wrap)")
        align_center_button.connect("clicked", self.on_table_align_center)
        self.table_toolbar.append(align_center_button)
        
        # Right alignment
        align_right_button = Gtk.Button(icon_name="table-align-right-symbolic")
        align_right_button.set_tooltip_text("Align Right (text wraps around left)")
        align_right_button.connect("clicked", self.on_table_align_right)
        self.table_toolbar.append(align_right_button)
        
        # Full width (no wrap)
        full_width_button = Gtk.Button(icon_name="table-align-full-width-symbolic")
        full_width_button.set_tooltip_text("Full Width (no text wrap)")
        full_width_button.connect("clicked", self.on_table_full_width)
        self.table_toolbar.append(full_width_button)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.table_toolbar.append(spacer)
        
        # Close button
        close_button = Gtk.Button(icon_name="window-close-symbolic")
        close_button.set_tooltip_text("Close table toolbar")
        close_button.connect("clicked", self.on_close_table_toolbar_clicked)
        self.table_toolbar.append(close_button)
        
        # Add table toolbar to main box but initially hidden
        # Insert it before the status bar, which should be the last child
        self.main_box.insert_child_after(self.table_toolbar, self.find_bar)
        self.table_toolbar.set_visible(False)

    # Now add the new table operation methods
    def on_add_row_above_clicked(self, button):
        """Add a row above the current row in the active table"""
        js_code = """
        (function() {
            if (!activeTable) return;
            
            // Get the current row index
            let selection = window.getSelection();
            if (selection.rangeCount < 1) return;
            
            let range = selection.getRangeAt(0);
            let cell = range.startContainer;
            
            // Find the TD/TH parent
            while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== activeTable) {
                cell = cell.parentNode;
            }
            
            if (!cell || (cell.tagName !== 'TD' && cell.tagName !== 'TH')) {
                // If no cell is selected, just add to the end
                addTableRow(activeTable);
                return;
            }
            
            // Find the TR parent
            let row = cell;
            while (row && row.tagName !== 'TR') {
                row = row.parentNode;
            }
            
            if (!row) return;
            
            // Find the row index
            let rowIndex = row.rowIndex;
            
            // Insert a new row above this one
            let newRow = activeTable.insertRow(rowIndex);
            
            // Add cells matching the selected row
            for (let i = 0; i < row.cells.length; i++) {
                let newCell = newRow.insertCell(i);
                newCell.innerHTML = ' ';
            }
            
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_add_row_below_clicked(self, button):
        """Add a row below the current row in the active table"""
        js_code = """
        (function() {
            if (!activeTable) return;
            
            // Get the current row index
            let selection = window.getSelection();
            if (selection.rangeCount < 1) return;
            
            let range = selection.getRangeAt(0);
            let cell = range.startContainer;
            
            // Find the TD/TH parent
            while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== activeTable) {
                cell = cell.parentNode;
            }
            
            if (!cell || (cell.tagName !== 'TD' && cell.tagName !== 'TH')) {
                // If no cell is selected, just add to the end
                addTableRow(activeTable);
                return;
            }
            
            // Find the TR parent
            let row = cell;
            while (row && row.tagName !== 'TR') {
                row = row.parentNode;
            }
            
            if (!row) return;
            
            // Find the row index
            let rowIndex = row.rowIndex;
            
            // Insert a new row below this one
            let newRow = activeTable.insertRow(rowIndex + 1);
            
            // Add cells matching the selected row
            for (let i = 0; i < row.cells.length; i++) {
                let newCell = newRow.insertCell(i);
                newCell.innerHTML = ' ';
            }
            
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_add_column_before_clicked(self, button):
        """Add a column before the current column in the active table"""
        js_code = """
        (function() {
            if (!activeTable) return;
            
            // Get the current cell index
            let selection = window.getSelection();
            if (selection.rangeCount < 1) return;
            
            let range = selection.getRangeAt(0);
            let cell = range.startContainer;
            
            // Find the TD/TH parent
            while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== activeTable) {
                cell = cell.parentNode;
            }
            
            if (!cell || (cell.tagName !== 'TD' && cell.tagName !== 'TH')) {
                // If no cell is selected, just add to the end
                addTableColumn(activeTable);
                return;
            }
            
            // Find the cell index
            let cellIndex = cell.cellIndex;
            
            // Add a column before the current one
            const rows = activeTable.rows;
            for (let i = 0; i < rows.length; i++) {
                const newCell = rows[i].insertCell(cellIndex);
                newCell.innerHTML = ' ';
            }
            
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_add_column_after_clicked(self, button):
        """Add a column after the current column in the active table"""
        js_code = """
        (function() {
            if (!activeTable) return;
            
            // Get the current cell index
            let selection = window.getSelection();
            if (selection.rangeCount < 1) return;
            
            let range = selection.getRangeAt(0);
            let cell = range.startContainer;
            
            // Find the TD/TH parent
            while (cell && cell.tagName !== 'TD' && cell.tagName !== 'TH' && cell !== activeTable) {
                cell = cell.parentNode;
            }
            
            if (!cell || (cell.tagName !== 'TD' && cell.tagName !== 'TH')) {
                // If no cell is selected, just add to the end
                addTableColumn(activeTable);
                return;
            }
            
            // Find the cell index
            let cellIndex = cell.cellIndex;
            
            // Add a column after the current one
            const rows = activeTable.rows;
            for (let i = 0; i < rows.length; i++) {
                const newCell = rows[i].insertCell(cellIndex + 1);
                newCell.innerHTML = ' ';
            }
            
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_delete_table_clicked(self, button):
        """Delete the entire table"""
        js_code = """
        (function() {
            if (!activeTable) return;
            
            // Remove the table
            activeTable.parentNode.removeChild(activeTable);
            
            // Clear active table reference
            activeTable = null;
            
            // Hide the table toolbar
            window.webkit.messageHandlers.tableDeleted.postMessage('table-deleted');
            
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        })();
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)
        
        # Hide the table toolbar since table was deleted
        self.table_toolbar.set_visible(False)

    # Add handlers for the table toolbar buttons
    def on_add_row_clicked(self, button):
        """Add a row to the active table"""
        js_code = "addTableRow(activeTable);"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_add_column_clicked(self, button):
        """Add a column to the active table"""
        js_code = "addTableColumn(activeTable);"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_delete_row_clicked(self, button):
        """Delete a row from the active table"""
        js_code = "deleteTableRow(activeTable);"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_delete_column_clicked(self, button):
        """Delete a column from the active table"""
        js_code = "deleteTableColumn(activeTable);"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_table_align_left(self, button):
        """Align table to the left with text wrapping around right"""
        js_code = """
        if (activeTable) {
            activeTable.className = 'left-align';
            activeTable.style.width = 'auto';
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        }
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_table_align_center(self, button):
        """Align table to the center with no text wrapping"""
        js_code = """
        if (activeTable) {
            activeTable.className = 'center-align';
            activeTable.style.width = 'auto';
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        }
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_table_align_right(self, button):
        """Align table to the right with text wrapping around left"""
        js_code = """
        if (activeTable) {
            activeTable.className = 'right-align';
            activeTable.style.width = 'auto';
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        }
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_table_full_width(self, button):
        """Make table full width with no text wrapping"""
        js_code = """
        if (activeTable) {
            activeTable.className = 'no-wrap';
            activeTable.style.width = '100%';
            window.webkit.messageHandlers.contentChanged.postMessage('changed');
        }
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    def on_close_table_toolbar_clicked(self, button):
        """Hide the table toolbar and deactivate tables"""
        self.status_label.set_text("Table toolbar closed")

        self.table_toolbar.set_visible(False)
        
        js_code = "deactivateAllTables();"
        self.webview.evaluate_javascript(js_code, -1, None, None, None, None)

    # Now let's create a function to show the table toolbar when a table is clicked
    def show_table_toolbar(self):
        """Show the table toolbar when a table is active"""
        self.table_toolbar.set_visible(True)

    def on_tables_deactivated(self, manager, message):
        """Handle event when all tables are deactivated"""
        self.table_toolbar.set_visible(False)
        self.status_label.set_text("No table selected")
        
    def on_table_deleted(self, manager, message):
        """Handle table deleted event from editor"""
        self.table_toolbar.set_visible(False)
        self.status_label.set_text("Table deleted")


def main():
    """Main function"""
    app = Writer()
    return app.run(sys.argv)

if __name__ == "__main__":
    # Initialize Adwaita
    Adw.init()
    
    # Run the app
    sys.exit(main())
