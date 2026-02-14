# ==========================
# 3ds Max Inspector
# IMAN SHIRANI
# V0.0.1
# GITHUB :
# https://github.com/imanshirani/3ds-Max-Inspector/
# PAYPAL DONATION : (if you like it and want to support me)
# https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4
# ==========================

from PySide6 import QtWidgets, QtCore, QtGui
import pymxs
import json
import os 

rt = pymxs.runtime

print(f"--- PYTHON DEBUG: Script file loaded. 'rt' object should be: {rt} ---")

def safe_repr(val):
    try:
        s = str(val)
        # More robust check for maxscript 'undefined'
        if s in ("undefined", "<undefined>", "Undef"):
            return ""
        return s
    except Exception:
        return "<unreadable>"

def get_type_name(val):
    try:
        try:
            cls = rt.classOf(val)
            return str(cls)
        except Exception:
            return type(val).__name__
    except Exception:
        return "unknown"

def try_classid(obj):
    try:
        try:
            cid = rt.classID(obj)
            return safe_repr(cid)
        except Exception:
            pass
        try:
            cid = getattr(obj, "classID", None)
            if cid is not None:
                return safe_repr(cid)
        except Exception:
            pass
    except Exception:
        pass
    return "<unknown>"

class MaxInspector(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        # --- CACHE ---
        try:
            script_path = os.path.realpath(__file__)
        except NameError:
            script_path = rt.getSourceFileName()
            if not script_path:
                print("--- PYTHON WARNING: Could not determine script path. Saving cache to C:/temp/ ---")
                if not os.path.exists("c:/temp"):
                    os.makedirs("c:/temp")
                script_path = "c:/temp/max_inspector.py"
                
        self._cache_file_path = os.path.join(os.path.dirname(script_path), "max_classes_cache.json")
        # --- END CACHE ---
        
        self.setWindowTitle("3DS Max Inspector — Script Helper")
        self.setMinimumSize(1000, 800)
        self._all_classes = []  # list of (name, super, classid, plugin)
        self._by_super = {}
        self._by_plugin = {}
        
        self.build_ui()
        self.populate_tree()
        
        # --- Auto-load from cache on startup ---
        self.load_from_cache()

    def build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        top_layout = QtWidgets.QHBoxLayout()

        # Left: Main scene tree
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setMinimumWidth(300)
        top_layout.addWidget(self.tree, 2)

        # Middle: Report & controls
        center_layout = QtWidgets.QVBoxLayout()
        btns_layout = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh Scene")
        self.btn_select_current = QtWidgets.QPushButton("Select Current Object")
        
        self.btn_load_classes = QtWidgets.QPushButton("Re-Scan All Classes (Slow)")
        self.btn_load_classes.setStyleSheet("background-color: #FFFFFF; color: #000000;") 
        
        self.btn_clear = QtWidgets.QPushButton("Clear Report")
        btns_layout.addWidget(self.btn_refresh)
        btns_layout.addWidget(self.btn_select_current)
        btns_layout.addWidget(self.btn_load_classes)
        btns_layout.addWidget(self.btn_clear)
        center_layout.addLayout(btns_layout)

        self.report = QtWidgets.QTextEdit()
        self.report.setReadOnly(True)
        self.report.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        font = self.report.font()
        font.setPointSize(10)
        self.report.setFont(font)
        center_layout.addWidget(self.report, 1)
        top_layout.addLayout(center_layout, 3)

        # Right: Classes area (tabbed: BySuper / ByPlugin / All)
        right_layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Classes")
        right_layout.addWidget(label)

        self.classes_tabs = QtWidgets.QTabWidget()
        # Tab 1: By SuperClass (Tree)
        self.tab_super = QtWidgets.QWidget()
        t1_layout = QtWidgets.QVBoxLayout(self.tab_super)
        self.tree_by_super = QtWidgets.QTreeWidget()
        self.tree_by_super.setHeaderLabels(["SuperClass -> Class"])
        self.tree_by_super.itemClicked.connect(self.on_class_tree_clicked)
        t1_layout.addWidget(self.tree_by_super)
        self.classes_tabs.addTab(self.tab_super, "By SuperClass")

        # Tab 2: By Plugin (Tree)
        self.tab_plugin = QtWidgets.QWidget()
        t2_layout = QtWidgets.QVBoxLayout(self.tab_plugin)
        self.tree_by_plugin = QtWidgets.QTreeWidget()
        self.tree_by_plugin.setHeaderLabels(["Plugin -> Class"])
        self.tree_by_plugin.itemClicked.connect(self.on_class_tree_clicked)
        t2_layout.addWidget(self.tree_by_plugin)
        self.classes_tabs.addTab(self.tab_plugin, "By Plugin")

        # Tab 3: All Classes (List + Search)
        self.tab_all = QtWidgets.QWidget()
        t3_layout = QtWidgets.QVBoxLayout(self.tab_all)
        search_row = QtWidgets.QHBoxLayout()
        self.class_search = QtWidgets.QLineEdit()
        self.class_search.setPlaceholderText("Search classes...")
        self.class_search.textChanged.connect(self.filter_all_classes)
        self.btn_copy_class = QtWidgets.QPushButton("Copy Selected")
        self.btn_copy_class.clicked.connect(self.copy_selected_class)
        search_row.addWidget(self.class_search)
        search_row.addWidget(self.btn_copy_class)
        t3_layout.addLayout(search_row)
        self.class_list = QtWidgets.QListWidget()
        self.class_list.itemClicked.connect(self.on_class_list_clicked)
        self.class_list.itemDoubleClicked.connect(self.copy_class_item)
        t3_layout.addWidget(self.class_list)
        self.classes_tabs.addTab(self.tab_all, "All Classes")

        # Helper function to create a new tab with a list
        def create_class_tab(name, tooltip):
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setContentsMargins(2, 2, 2, 2) # Make it tight
            class_list = QtWidgets.QListWidget()
            class_list.itemClicked.connect(self.on_class_list_clicked)
            class_list.itemDoubleClicked.connect(self.copy_class_item)
            layout.addWidget(class_list)
            self.classes_tabs.addTab(tab, name)
            self.classes_tabs.setTabToolTip(self.classes_tabs.count() - 1, tooltip)
            return class_list

        self.list_superclasses = create_class_tab("SuperClasses", "Core MaxScript SuperClasses (classOf, superClassOf, ...)")
        self.list_geometry = create_class_tab("Geometry", "geometry.classes (Box, Sphere, Editable_Poly...)")
        self.list_shapes = create_class_tab("Shapes", "shape.classes (Line, Circle, Text...)")
        self.list_lights = create_class_tab("Lights", "light.classes (Omni, Spot, VrayLight...)")
        self.list_cameras = create_class_tab("Cameras", "camera.classes (FreeCamera, TargetCamera...)")
        self.list_helpers = create_class_tab("Helpers", "helper.classes (Point, Dummy, Protractor...)")
        self.list_modifiers = create_class_tab("Modifiers", "modifier.classes (Bend, UVW_Map, Edit_Poly...)")
        self.list_spacewarps = create_class_tab("SpaceWarps", "spacewarp.classes (Gravity, Wind, Displace...)")
        self.list_materials = create_class_tab("Materials", "material.classes (Standard, Physical, VrayMtl...)")
        self.list_textures = create_class_tab("Textures", "textureMap.classes (Bitmap, Noise, Gradient...)")
        self.list_effects = create_class_tab("RenderFX", "renderEffect.classes (Blur, File_Output, VrayDenoiser...)")

        right_layout.addWidget(self.classes_tabs, 3)

        # Class info box
        right_layout.addWidget(QtWidgets.QLabel("Class Info:"))
        self.class_info = QtWidgets.QTextEdit()
        self.class_info.setReadOnly(True)
        self.class_info.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        right_layout.addWidget(self.class_info, 2)

        top_layout.addLayout(right_layout, 2)

        main_layout.addLayout(top_layout)
        
        # --- ADDED: Progress Bar ---
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False) # Hide it by default
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)
        # --- END ADDED ---

        # Connect basic buttons
        self.btn_refresh.clicked.connect(self.populate_tree)
        self.btn_select_current.clicked.connect(self.select_current_object)
        self.btn_clear.clicked.connect(self.report.clear)
        self.btn_load_classes.clicked.connect(self.run_full_scan)

    def log(self, text):
        self.report.append(text)

    def populate_tree(self):
        self.tree.clear()
        
        obj_root = QtWidgets.QTreeWidgetItem(self.tree, ["Object"])
        scene_root = QtWidgets.QTreeWidgetItem(self.tree, ["Scene"])
        system_root = QtWidgets.QTreeWidgetItem(self.tree, ["System"])
        render_root = QtWidgets.QTreeWidgetItem(self.tree, ["Render / Environment"])

        for name in ["Properties", "Methods", "Material", "Modifiers", "Controllers",
                     "Custom Attributes", "User Properties", "Transform Matrix", "Base Params", "Class Info"]:
            QtWidgets.QTreeWidgetItem(obj_root, [name])

        QtWidgets.QTreeWidgetItem(scene_root, ["All Objects (expand)"])
        objects_container = QtWidgets.QTreeWidgetItem(scene_root, ["Objects"])
        try:
            for o in rt.objects:
                try:
                    item = QtWidgets.QTreeWidgetItem(objects_container, [safe_repr(o.name)])
                    item.setData(0, QtCore.Qt.UserRole, ("scene_obj", o))
                except Exception:
                    pass
        except Exception:
            pass
            
        for name in ["Scene Info", "File Info", "Units Setup", "Selection Sets"]:
            QtWidgets.QTreeWidgetItem(scene_root, [name])

        for name in ["gw (Graphics Window)", "callbacks", "Viewports", "Material Editor", "Plugins / Classes"]:
            QtWidgets.QTreeWidgetItem(system_root, [name])

        for name in ["Render Settings", "Environment Map", "Renderers.Current", "Exposure/Color Management"]:
            QtWidgets.QTreeWidgetItem(render_root, [name])
            
        self.tree.expandAll()

    # --- Inspector functions (V5.9) ---
    def select_current_object(self):
        try:
            if rt.selection.count > 0:
                obj = rt.selection[0]
                self.log(f"Selected current object: {safe_repr(obj.name)} ({get_type_name(obj)})")
            else:
                self.log("? No object selected in the scene.")
        except Exception as e:
            self.log("Error selecting current object: " + str(e))
            
    def on_item_clicked(self, item, col):
        data = item.data(0, QtCore.Qt.UserRole)
        if data and isinstance(data, tuple) and data[0] == "scene_obj":
            obj = data[1]
            self.inspect_object_all(obj)
            return
        text = item.text(0)
        
        try:
            if text == "Properties": self.inspect_selected("properties")
            elif text == "Methods": self.inspect_selected("methods")
            elif text == "Material": self.inspect_selected("material")
            elif text == "Modifiers": self.inspect_selected("modifiers")
            elif text == "Controllers": self.inspect_selected("controllers")
            elif text == "Custom Attributes": self.inspect_selected("custom_attributes")
            elif text == "User Properties": self.inspect_selected("user_properties")
            elif text == "Transform Matrix": self.inspect_selected("transform")
            elif text == "Base Params": self.inspect_selected("base_params")
            elif text == "Class Info": self.inspect_selected("class_info")
            elif text == "All Objects (expand)": self.inspect_scene_objects()
            elif text == "Scene Info": self.inspect_scene_info()
            elif text == "File Info": self.inspect_file_info()
            elif text == "Units Setup": self.inspect_units()
            elif text == "Selection Sets": self.inspect_selection_sets()
            elif text == "gw (Graphics Window)": self.inspect_gw()
            elif text == "callbacks": self.inspect_callbacks()
            elif text == "Viewports": self.inspect_viewports()
            elif text == "Material Editor": self.inspect_material_editor()
            elif text == "Plugins / Classes":
                self.classes_tabs.setCurrentIndex(0)
                self.class_list.setFocus()
            elif text == "Render Settings": self.inspect_render_settings()
            elif text == "Environment Map": self.inspect_environment()
            elif text == "Renderers.Current": self.inspect_current_renderer()
            elif text == "Exposure/Color Management": self.inspect_color_mgmt()
            else: self.log(f"Clicked: {text}")
        except Exception as e:
            self.log(f"--- CRITICAL ERROR processing click for '{text}' ---")
            self.log(f"--- {e} ---")
        
    def get_target_object(self):
        if rt.selection.count > 0: return rt.selection[0]
        else:
            self.log("? No object selected. Select an object or click Scene -> Objects -> <name>.")
            return None
            
    def inspect_selected(self, mode):
        obj = self.get_target_object()
        if not obj: return
        if mode == "properties": self.inspect_properties(obj)
        elif mode == "methods": self.inspect_methods(obj)
        elif mode == "material": self.inspect_material(obj)
        elif mode == "modifiers": self.inspect_modifiers(obj)
        elif mode == "controllers": self.inspect_controllers(obj)
        elif mode == "custom_attributes": self.inspect_custom_attributes(obj)
        elif mode == "user_properties": self.inspect_user_properties(obj)
        elif mode == "transform": self.inspect_transform(obj)
        elif mode == "base_params": self.inspect_base_params(obj)
        elif mode == "class_info": self.inspect_class_info(obj)
        
    def inspect_object_all(self, obj):
        self.log(f"\n=== Inspect: {safe_repr(obj.name)} ({get_type_name(obj)}) ===")
        self.inspect_properties(obj); self.inspect_material(obj); self.inspect_modifiers(obj)
        self.inspect_controllers(obj); self.inspect_methods(obj); self.inspect_class_info(obj)
        self.inspect_base_params(obj); self.inspect_custom_attributes(obj); self.inspect_user_properties(obj)
        self.log("\n")
        
    def inspect_properties(self, obj):
        self.log(f"\n--- Properties of {safe_repr(obj.name)} ---")
        try: names = rt.getPropNames(obj)
        except Exception: names = []
        for p in names:
            try:
                val = rt.getProperty(obj, p); t = get_type_name(val); rep = safe_repr(val)
                self.log(f"{p} ({t}) = {rep}")
            except Exception: self.log(f"{p} (unknown) = <unreadable>")
        if not names: self.log("<no properties found or unreadable>"); self.log("")
        
    def inspect_methods(self, obj):
        self.log(f"\n--- Methods of {safe_repr(obj.name)} ---")
        try:
            for m in rt.getMethods(obj): self.log(str(m))
        except Exception: 
            self.log("<unable to retrieve methods (rt.getMethods failed)>"); 
        self.log("")
        
    def inspect_material(self, obj):
        self.log(f"\n--- Material of {safe_repr(obj.name)} ---")
        try:
            mat = obj.material
            if not mat: self.log("No Material assigned!"); return
            self.log(f"Material: {safe_repr(mat)} ({get_type_name(mat)})")
            try: props = rt.getPropNames(mat)
            except Exception: props = []
            for p in props:
                try: v = rt.getProperty(mat, p); self.log(f"{p} ({get_type_name(v)}) = {safe_repr(v)}")
                except Exception: self.log(f"{p} = <unreadable>")
        except Exception as e: self.log("Error reading material: " + str(e)); self.log("")
        
    def inspect_modifiers(self, obj):
        self.log(f"\n--- Modifiers on {safe_repr(obj.name)} ---")
        try:
            try: mods = list(obj.modifiers)
            except Exception: mods = obj.modifiers if hasattr(obj, "modifiers") else []
            if not mods: self.log("<no modifiers>"); return
            for m in mods:
                self.log(f"> {safe_repr(m)} ({get_type_name(m)})")
                try: props = rt.getPropNames(m)
                except Exception: props = []
                for p in props:
                    try: v = rt.getProperty(m, p); self.log(f"  {p} ({get_type_name(v)}) = {safe_repr(v)}")
                    except Exception: self.log(f"  {p} = <unreadable>")
        except Exception as e: self.log("Error reading modifiers: " + str(e)); self.log("")
        
    def inspect_controllers(self, obj):
        self.log(f"\n--- Controllers of {safe_repr(obj.name)} ---")
        # --- V5.8: Using safer rt.getPropertyController ---
        try:
            for prop_name in ["position", "rotation", "scale"]:
                try: 
                    ctrl = rt.getPropertyController(obj, prop_name)
                    self.log(f"{prop_name.capitalize()} ({get_type_name(ctrl)}) = {safe_repr(ctrl)}")
                except Exception: 
                    self.log(f"{prop_name.capitalize()} = <unreadable>")
        except Exception as e: 
            self.log("Error reading controllers: " + str(e)); 
        self.log("")
        
    # --- V5.8: IMPLEMENTED ---
    def inspect_custom_attributes(self, obj): 
        self.log(f"\n--- Custom Attributes of {safe_repr(obj.name)} ---")
        try:
            ca_defs = rt.custAttributes.getDefs(obj)
            if not ca_defs or ca_defs.count == 0:
                self.log("<no custom attributes found>")
                self.log("")
                return
            
            for ca_def in ca_defs:
                self.log(f"Definition: {safe_repr(ca_def.name)}")
                ca_block = rt.custAttributes.get(obj, ca_def)
                for p in rt.getPropNames(ca_block):
                    try:
                        v = rt.getProperty(ca_block, p)
                        self.log(f"  .{p} ({get_type_name(v)}) = {safe_repr(v)}")
                    except Exception:
                        self.log(f"  .{p} = <unreadable>")
        except Exception as e:
            self.log(f"<unable to read custom attributes: {e}>")
        self.log("")

    # --- V5.8: IMPLEMENTED ---
    def inspect_user_properties(self, obj): 
        self.log(f"\n--- User Properties of {safe_repr(obj.name)} ---")
        try:
            buf = rt.getUserPropBuffer(obj)
            if not buf:
                self.log("<no user properties>")
            else:
                self.log(buf)
        except Exception as e:
            self.log(f"<unable to read user properties: {e}>")
        self.log("")

    def inspect_transform(self, obj): 
        self.log(f"\n--- Transform Matrix of {safe_repr(obj.name)} ---"); 
        try:
            self.log(safe_repr(obj.transform))
        except Exception as e:
            self.log(f"<unable to read transform: {e}>")
        self.log("")

    # --- V5.8: IMPLEMENTED ---
    def inspect_base_params(self, obj): 
        self.log(f"\n--- Base Params of {safe_repr(obj.name)} ---")
        common_params = ['radius', 'length', 'width', 'height', 'segs', 'sides', 'capsegs']
        found_any = False
        for p in common_params:
            try:
                # Use getattr for Python-side check, safer than rt.getProperty
                v = getattr(obj, p) 
                self.log(f"{p} ({get_type_name(v)}) = {safe_repr(v)}")
                found_any = True
            except Exception:
                pass # Property doesn't exist on this object, skip silently
        if not found_any:
            self.log("<no common base parameters found>")
        self.log("")
    
    def inspect_class_info(self, obj):
        self.log(f"\n--- Class Info for {safe_repr(obj.name)} ---")
        try:
            try: mxs_cls = rt.classOf(obj)
            except Exception: mxs_cls = "<unknown>"
            
            # --- V5.6 SAFE SUPERCLASS ---
            try: super_cls = rt.superClassOf(obj)
            except Exception: super_cls = "<unknown (superClassOf failed)>"
                
            py_type = type(obj).__name__; cid = try_classid(obj)
            self.log(f"MXS Class: {safe_repr(mxs_cls)}"); self.log(f"SuperClass: {safe_repr(super_cls)}")
            self.log(f"Python Type: {py_type}"); self.log(f"ClassID: {cid}")
        except Exception as e: self.log("Error reading class info: " + str(e)); self.log("")
        
    def inspect_scene_objects(self): self.log("\n--- Scene Objects ---"); [self.log(f"{safe_repr(o.name)} ({get_type_name(o)})") for o in rt.objects]; self.log("")
    
    # --- V5.9: PARANOID MODE ---
    def inspect_scene_info(self): 
        self.log("\n--- Scene Info ---")
        try:
            try: self.log(f"Scene name: {safe_repr(rt.filename)}")
            except Exception: self.log(f"Scene name: {safe_repr(rt.maxFileName)}") # Fallback
        except Exception: self.log("Scene name: <failed to get>")
        try: self.log(f"Num objects: {len(list(rt.objects))}")
        except Exception: self.log("Num objects: <failed to get>")
        self.log("")

    # --- V5.9: PARANOID MODE ---
    def inspect_file_info(self): 
        self.log("\n--- File Info ---")
        try:
            try: self.log(f"Filename: {safe_repr(rt.filename)}")
            except Exception: self.log(f"Filename: {safe_repr(rt.maxFileName)}") # Fallback
        except Exception: self.log("Filename: <failed to get>")
        self.log("")
        
    def inspect_units(self): self.log("\n--- Units Setup ---"); self.log(safe_repr(rt.units)); self.log("")
    def inspect_selection_sets(self): self.log("\n--- Selection Sets ---"); [self.log(safe_repr(s)) for s in rt.selectionSets]; self.log("")
    def inspect_plugins(self): self.log("\n--- Plugins / Classes (short) ---"); [self.log(safe_repr(c)) for c in rt.pluginClasses]; self.log("")
    def inspect_environment(self): self.log("\n--- Environment / EnvironmentMap ---"); self.log(f"EnvMap: {safe_repr(rt.environmentMap)}"); self.log("")
    def inspect_current_renderer(self): self.log("\n--- Renderer.Current ---"); self.log(safe_repr(rt.renderers.current)); self.log("")

    # -----------------------------------------------------------------
    # --- IMPLEMENTED placeholder functions (V5.10) ---
    # -----------------------------------------------------------------
    
    def inspect_gw(self):
        self.log("\n--- GW (Graphics Window) ---")
        try:
            props = rt.getPropNames(rt.gw)
            for p in props:
                try:
                    v = rt.getProperty(rt.gw, p)
                    self.log(f"{p} ({get_type_name(v)}) = {safe_repr(v)}")
                except Exception:
                    self.log(f"{p} = <unreadable>")
        except Exception as e:
            self.log(f"Error reading rt.gw properties: {e}")
        self.log("")

    def inspect_callbacks(self):
        self.log("\n--- Callbacks ---")
        try:
            self.log("Listing callback items (use 'callbacks.show()' in Listener for details):")
            props = rt.getPropNames(rt.callbacks)
            for p in props:
                try:
                    v = rt.getProperty(rt.callbacks, p)
                    self.log(f".{p} = {safe_repr(v)}")
                except Exception:
                    self.log(f".{p} = <unreadable>")
        except Exception as e:
            self.log(f"Error reading rt.callbacks: {e}")
        self.log("")

    # --- V5.9: PARANOID MODE ---
    def inspect_viewports(self):
        self.log("\n--- Viewports ---")
        try:
            try: self.log(f"Active Viewport Index: {rt.viewport.activeViewport}")
            except Exception: self.log("Active Viewport Index: <failed>")
            try: self.log(f"Layout: {rt.viewport.layout}")
            except Exception: self.log("Layout: <failed>")
            
            try:
                num_vps = rt.viewport.GetNumViewports() # Modern, safer method
            except Exception:
                self.log("Number of Viewports: <failed to get count>")
                self.log("")
                return
            
            self.log(f"Number of Viewports: {num_vps}")
            
            for i in range(1, num_vps + 1):
                self.log(f"\n--- Viewport {i} ---")
                try: self.log(f"Type: {rt.viewport.getType(index=i)}")
                except Exception: self.log("Type: <failed>")
                try: self.log(f"Camera: {safe_repr(rt.viewport.getCamera(index=i))}")
                except Exception: self.log("Camera: <failed>")
                try: self.log(f"Shading: {rt.viewport.getShading(index=i)}")
                except Exception: self.log("Shading: <failed>")
                try: self.log(f"Is Wireframe: {rt.viewport.isWireframe(index=i)}")
                except Exception: self.log("Is Wireframe: <failed>")
                        
        except Exception as e:
            self.log(f"Error reading rt.viewport: {e}")
        self.log("")
        
    # --- V5.10: Using Functions instead of Properties ---
    def inspect_material_editor(self):
        self.log("\n--- Material Editor (MEdit / SME) ---")
        try:
            self.log("--- Compact Material Editor (rt.matEditor) ---")
            active_slot_index = 1 # Default to 1
            try: 
                self.log(f"Is Open: {rt.matEditor.isOpen()}")
            except Exception: self.log("Is Open: <failed>")
            try: 
                active_slot_index = rt.matEditor.GetActiveSlot() # <-- V5.10 FIX
                self.log(f"Active Slot Index: {active_slot_index}")
            except Exception: self.log(f"Active Slot Index: <failed, assuming 1>")
            
            self.log("\n--- Slate Material Editor (rt.sme) ---")
            try: self.log(f"Is Open: {rt.sme.isOpen()}")
            except Exception: self.log("Is Open: <failed>")
            try: 
                active_view = rt.sme.GetActiveView() # <-- V5.10 FIX
                self.log(f"Active View Name: {active_view.name if active_view else 'None'}")
            except Exception: self.log("Active View Name: <failed>")
            
            self.log(f"\n--- Active Material (from Compact Slot {active_slot_index}) ---")
            try:
                active_mat = rt.matEditor.GetMtl(active_slot_index) # Use the index we found
                self.log(f"Material: {safe_repr(active_mat)}")
                
                if active_mat:
                    self.log("--- Properties of Active Material ---")
                    props = rt.getPropNames(active_mat)
                    for p in props:
                        try:
                            v = rt.getProperty(active_mat, p)
                            self.log(f"{p} ({get_type_name(v)}) = {safe_repr(v)}")
                        except Exception:
                            self.log(f"{p} = <unreadable>")
            except Exception:
                self.log("Could not get active material slot.")
                        
        except Exception as e:
            self.log(f"Error reading Material Editor properties: {e}")
        self.log("")

    # --- V5.9: PARANOID MODE ---
    def inspect_render_settings(self):
        self.log("\n--- Render Settings ---")
        try:
            self.log(f"Range: {safe_repr(rt.renderSceneDialog.timeType)}")
        except Exception:
            self.log("Range: (Attribute 'timeType' not found)")
        try:
            self.log(f"W: {safe_repr(rt.renderWidth)} H: {safe_repr(rt.renderHeight)}")
        except Exception:
            self.log("W/H: (Attributes 'renderWidth/Height' not found)")
        self.log("")

    # --- V5.9: PARANOID MODE ---
    def inspect_color_mgmt(self):
        self.log("\n--- Color / Exposure Management ---")
        try:
            self.log(safe_repr(rt.colorManager))
        except Exception:
            self.log("(Attribute 'colorManager' not found)")
        self.log("")
        
    # -----------------------------------------------------------------
    # --- CORE FUNCTIONS (SCAN, CACHE, POPULATE) (V5.2) ---
    # -----------------------------------------------------------------
    
    def load_from_cache(self):
        """Tries to load class data from the JSON cache file."""
        self.log(f"--- PYTHON: Looking for cache file: {self._cache_file_path} ---")
        if not os.path.exists(self._cache_file_path):
            self.log("--- PYTHON: Cache file not found. ---")
            self.log("--- Please click 'Re-Scan All Classes' to build the class list. ---")
            return False
            
        try:
            self.log("--- PYTHON: Cache file found. Loading... ---")
            with open(self._cache_file_path, 'r') as f:
                cached_data = json.load(f) # This loads a list of lists

            if not cached_data:
                self.log("--- PYTHON: Cache file is empty. ---")
                self.log("--- Please click 'Re-Scan All Classes' to rebuild. ---")
                return False
                
            self.log(f"--- PYTHON: Cache loaded. Found {len(cached_data)} classes. Populating UI... ---")
            
            # This is the key call, now with the V5.2 fix
            self.populate_ui_from_data(cached_data) 
            
            self.log("--- PYTHON: UI populated from cache. Ready. ---")
            return True
            
        except Exception as e:
            self.log(f"--- PYTHON ERROR: Failed to read or parse cache file! ---")
            self.log(f"--- ERROR: {e} ---")
            self.log("--- Cache may be corrupt. Please run 'Re-Scan All Classes' to rebuild it. ---")
            return False

    def save_to_cache(self):
        """Saves the current _all_classes list to the JSON cache file."""
        if not self._all_classes:
            self.log("--- PYTHON Warning: No classes to save. Cache not written. ---")
            return
            
        self.log(f"--- PYTHON: Saving {len(self._all_classes)} classes to cache file... ---")
        try:
            # self._all_classes is a list of tuples, which json saves as a list of lists
            with open(self._cache_file_path, 'w') as f:
                json.dump(self._all_classes, f, indent=2)
            self.log(f"--- PYTHON: Cache file saved successfully to: {self._cache_file_path} ---")
        except Exception as e:
            self.log(f"--- PYTHON ERROR: Failed to save cache file! ---")
            self.log(f"--- ERROR: {e} ---")

    # --- V5.1 SCAN FUNCTION ---
    # This uses the Python loop (V4) but with the manual
    # SuperClass assignment (V5) to bypass rt.superClassOf()
    def run_full_scan(self):
        """
        Performs a full, slow scan by collecting classes from all
        individual categories, updating a progress bar.
        """
        self.log("--- PYTHON: Starting new full class scan (V5.1 Logic)... ---")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        scanned_data = []
        failed_classes = []
        
        # This is the list of all "SuperClass.classes" collections
        # We access them via 'rt' (Python) which is safe.
        # We manually pair them with their proper SuperClass name.
        categories_to_scan = [
            ("Modifier", rt.Modifier),
            ("Light", rt.Light),
            ("GeometryClass", rt.GeometryClass),
            ("Shape", rt.Shape),
            ("Camera", rt.Camera),
            ("Helper", rt.Helper),
            ("SpacewarpObject", rt.SpacewarpObject),
            ("Material", rt.Material),
            ("TextureMap", rt.TextureMap),
            ("RenderEffect", rt.RenderEffect),
            ("Atmospheric", rt.Atmospheric),
        ]
        
        # --- V5.9 HACK FIX: Try rt.Bezier_Float, a very common controller ---
        try:
            pos_controller_class = rt.classOf(rt.Bezier_Float) 
            # We assume rt.superClassOf is safe ONCE for a known object
            controller_superclass = rt.superClassOf(pos_controller_class)
            categories_to_scan.append(("Controller", controller_superclass))
            self.log("--- PYTHON: Found 'Controller' SuperClass via hack. ---")
        except Exception as e:
            self.log(f"--- PYTHON: Could not find 'Controller' class list: {e} ---")
            self.log("--- (This is non-critical, Controller tab may be incomplete) ---")

        
        try:
            self.log("--- PYTHON: Collecting class lists from all categories...")
            
            # --- Step 1: Collect all class lists into one big list ---
            self.progress_bar.setFormat("Collecting class lists...")
            QtWidgets.QApplication.processEvents()
            
            # This list will hold tuples of (class_object, superclass_name_string)
            class_object_pairs = []
            
            for superclass_name, class_collection_obj in categories_to_scan:
                try:
                    mxs_class_list = class_collection_obj.classes
                    if mxs_class_list is not None:
                        for c in mxs_class_list:
                            class_object_pairs.append((c, superclass_name))
                    else:
                        self.log(f"--- Warning: {superclass_name}.classes was None.")
                except Exception as e:
                    self.log(f"--- Error collecting {superclass_name}.classes: {e}")

            # --- Step 2: Scan the big list (just like before) ---
            total_classes = len(class_object_pairs)
            if total_classes == 0:
                self.log(f"--- PYTHON CRITICAL ERROR: Collected 0 classes from all categories! ---")
                self.log(f"--- This should not happen. Scan aborted. ---")
                print(f"--- PYTHON DEBUG: Collected 0 classes. Aborting. ---")
                self.progress_bar.setVisible(False)
                return

            self.progress_bar.setRange(0, total_classes)
            self.log(f"--- PYTHON: Found {total_classes} classes to scan. ---")
            print(f"--- PYTHON DEBUG: Starting scan of {total_classes} classes... ---")

            # Loop through all collected classes
            for i, (c, sc) in enumerate(class_object_pairs):
                # Update progress bar
                self.progress_bar.setValue(i + 1)
                
                if i % 50 == 0: # Update every 50 classes
                    QtWidgets.QApplication.processEvents()
                    self.progress_bar.setFormat(f"Scanning: {i}/{total_classes}...")
                
                try:
                    cname = safe_repr(c)
                    if not cname or cname == "<Unstringable Class>":
                        failed_classes.append(f"Class_{i}_Unstringable")
                        continue

                    # We use the 'sc' (superclass_name) we already have
                    
                    # We still *try* to get classID and pluginName,
                    # wrapping them in safe calls.
                    try:
                        cid = safe_repr(rt.classID(c))
                    except Exception:
                        cid = ""
                        
                    try:
                        pname = safe_repr(rt.pluginName(c))
                    except Exception:
                        pname = ""
                    
                    scanned_data.append((cname, sc, cid, pname))
                    
                except Exception as e_inner:
                    failed_classes.append(cname if 'cname' in locals() else f"Class_{i}_Error: {e_inner}")
            
            self.log("--- PYTHON: Scan complete. ---")
            print("--- PYTHON DEBUG: Scan complete. ---")
            if failed_classes:
                self.log(f"--- PYTHON: Warning: Failed to parse {len(failed_classes)} classes. ---")
                print(f"--- PYTHON DEBUG: Failed classes: {failed_classes} ---")

        except Exception as e:
            self.log(f"--- PYTHON CRITICAL ERROR during scan loop! ---")
            self.log(f"--- ERROR: {e} ---")
            print(f"--- PYTHON CRITICAL ERROR during scan loop! Error: {e} ---")
            self.progress_bar.setVisible(False)
            return

        # --- Success! ---
        self.progress_bar.setVisible(False)
        self.log(f"--- PYTHON: Populating UI with {len(scanned_data)} new classes... ---")
        
        # Populate all UI elements with the new data
        self.populate_ui_from_data(scanned_data)
        
        # Save the new data to the cache
        self.save_to_cache()
        self.log("--- PYTHON: New scan complete. UI populated and cache saved. ---")


    # --- V5.2 FIX: This function now correctly handles loading from JSON ---
    def populate_ui_from_data(self, class_data_list):
        """
        Clears and populates all class lists and trees from a
        list of (cname, sc, cid, pname) tuples OR lists.
        """
        # Clear all UI lists first
        self.class_list.clear()
        self.tree_by_super.clear()
        self.tree_by_plugin.clear()
        self.list_geometry.clear()
        self.list_shapes.clear()
        self.list_lights.clear()
        self.list_cameras.clear()
        self.list_helpers.clear()
        self.list_modifiers.clear()
        self.list_spacewarps.clear()
        self.list_materials.clear()
        self.list_textures.clear()
        self.list_effects.clear()
        self.list_superclasses.clear()

        # (We still populate SuperClasses manually)
        super_list = ["Node", "GeometryClass", "Shape", "Light", "Camera", "Helper", 
                      "Modifier", "SpacewarpObject", "Material", "TextureMap", 
                      "RenderEffect", "Controller", "Texmap", "Mtl", "Atmospheric", 
                      "maxObject", "Value"]
        self.list_superclasses.addItems(sorted(super_list, key=lambda x: x.lower()))

        # Define buckets
        buckets = {
            "GeometryClass": [], "Shape": [], "Light": [], "Camera": [],
            "Helper": [], "Modifier": [], "SpacewarpObject": [],
            "Material": [], "TextureMap": [], "RenderEffect": []
        }
        
        # --- V5.2 FIX ---
        # When loading from JSON, class_data_list is a list of LISTS [].
        # Lists are not hashable and cannot be used by dict.fromkeys().
        # We must convert them back to TUPLES () first.
        try:
            # Convert [c, s, cid, p] to (c, s, cid, p)
            hashable_data = [tuple(item) for item in class_data_list]
            # Now de-duplicate using the tuples
            unique_class_data = list(dict.fromkeys(hashable_data))
        except Exception as e:
            self.log(f"--- PYTHON ERROR: Could not de-duplicate class list: {e} ---")
            # Fallback: just use the raw list (might have duplicates)
            unique_class_data = [tuple(item) for item in class_data_list]
        # --- END V5.2 FIX ---
        
        # Store the master list
        self._all_classes = sorted(unique_class_data, key=lambda x: x[0].lower())
        
        # Reset dictionaries
        self._by_super = {}
        self._by_plugin = {}

        # Process the data list
        for cname, sc, cid, pname in self._all_classes:
            # Add to 'All Classes' tab
            self.class_list.addItem(cname)
            
            # Add to categorized buckets
            if sc in buckets:
                buckets[sc].append(cname)

            # Add to 'By SuperClass' tree data
            key_sc = sc if sc else "<no_super>"
            self._by_super.setdefault(key_sc, []).append((cname, cid, pname))
            
            # Add to 'By Plugin' tree data
            key_p = pname if pname else "<core>"
            self._by_plugin.setdefault(key_p, []).append((cname, sc, cid))

        # --- Populate all UI elements ---

        # Populate categorized lists from buckets
        list_mapping = {
            "GeometryClass": self.list_geometry, "Shape": self.list_shapes,
            "Light": self.list_lights, "Camera": self.list_cameras,
            "Helper": self.list_helpers, "Modifier": self.list_modifiers,
            "SpacewarpObject": self.list_spacewarps, "Material": self.list_materials,
            "TextureMap": self.list_textures, "RenderEffect": self.list_effects
        }
        for sc, widget in list_mapping.items():
            class_list = sorted(buckets.get(sc, []), key=lambda x: x.lower())
            widget.addItems(class_list)

        # Populate tree_by_super
        for sc in sorted(self._by_super.keys(), key=lambda x: x.lower()):
            parent = QtWidgets.QTreeWidgetItem(self.tree_by_super, [sc])
            for cname, cid, pname in sorted(self._by_super[sc], key=lambda x: x[0].lower()):
                child = QtWidgets.QTreeWidgetItem(parent, [cname])
                child.setData(0, QtCore.Qt.UserRole, ("class", cname, sc, cid, pname))

        # Populate tree_by_plugin
        for p in sorted(self._by_plugin.keys(), key=lambda x: x.lower()):
            parent = QtWidgets.QTreeWidgetItem(self.tree_by_plugin, [p])
            for cname, sc, cid in sorted(self._by_plugin[p], key=lambda x: x[0].lower()):
                child = QtWidgets.QTreeWidgetItem(parent, [cname])
                child.setData(0, QtCore.Qt.UserRole, ("class", cname, sc, cid, p))

        # Expand trees
        self.tree_by_super.expandToDepth(0)
        self.tree_by_plugin.expandToDepth(0)
    
    # --- END NEW CORE FUNCTIONS ---
    # --------------------------------

    def filter_all_classes(self, text):
        text = text.strip().lower()
        self.class_list.clear()
        if not text:
            for cname, sc, cid, pname in self._all_classes:
                self.class_list.addItem(cname)
            return
        for cname, sc, cid, pname in self._all_classes:
            if text in cname.lower() or text in sc.lower() or text in pname.lower():
                self.class_list.addItem(cname)

    # --- REVERTED (V5.4) ---
    # This now only shows cached info and avoids the 'getDefinition' error
    def on_class_list_clicked(self, item):
        name = item.text()
        
        # Handle clicks on the static "SuperClasses" tab first
        if self.classes_tabs.currentWidget() == self.list_superclasses.parentWidget():
             self.class_info.setPlainText(f"SuperClass: {name}\n(This is a base MaxScript class)")
             return
        
        # Find the class in our master list
        match = next(((c,sid,cid,p) for (c,sid,cid,p) in self._all_classes if c == name), None)
        
        if match:
            cname, sc, cid, pname = match
            # Just display the cached info
            self.class_info.setPlainText(
                f"Class: {cname}\n"
                f"SuperClass: {sc}\n"
                f"ClassID: {cid}\n"
                f"Plugin: {pname}\n"
            )
        else:
            self.class_info.setPlainText(f"Class: {name}\n(no extra info)")

    # --- REVERTED (V5.4) ---
    def on_class_tree_clicked(self, item, col=0):
        data = item.data(0, QtCore.Qt.UserRole)
        
        if data and data[0] == "class":
            # Item is a class
            _, cname, sc, cid, pname = data
            # Just display the cached info
            self.class_info.setPlainText(
                f"Class: {cname}\n"
                f"SuperClass: {sc}\n"
                f"ClassID: {cid}\n"
                f"Plugin: {pname}\n"
            )
        else:
            # Item is a parent (category)
            self.class_info.setPlainText(f"{item.text(0)}")

    def copy_class_item(self, item):
        name = item.text()
        QtWidgets.QApplication.clipboard().setText(name)
        self.log(f"Copied class name to clipboard: {name}")

    def copy_selected_class(self):
        it = self.class_list.currentItem()
        if it:
            QtWidgets.QApplication.clipboard().setText(it.text())
            self.log(f"Copied class name to clipboard: {it.text()}")
        else:
            self.log("No class selected to copy.")

# Launch
def run_inspector():
    global _max_inspector_ui
    try:
        _max_inspector_ui.close()
    except Exception:
        pass
    
    try:
        _max_inspector_ui = MaxInspector()
        _max_inspector_ui.show()
        print("--- PYTHON DEBUG: MaxInspector UI is running. ---")
    except Exception as e:
        print(f"--- PYTHON CRITICAL ERROR: Failed to create MaxInspector UI! ---")
        print(f"--- ERROR: {e} ---")
        try:
            rt.execute(f'format "--- PYTHON CRITICAL ERROR: Failed to create MaxInspector UI! Error: {e} ---\n"')
        except:
            pass
            
# Run when executed
run_inspector()