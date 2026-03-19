# 3ds Max Inspector (PySide6)

A powerful, user-friendly inspection tool for **Autodesk 3ds Max** developers and technical artists. Built with Python and PySide6, this tool allows you to explore scene objects, classes, plugins, and properties in real-time.

Developed by: **Iman Shirani**

[![Donate ❤️](https://img.shields.io/badge/Donate-PayPal-00457C?style=flat-square&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4)
![3dsmax](https://img.shields.io/badge/Autodesk-3ds%20Max-0696D7?style=flat-square&logo=autodesk)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

![screenshot](3DSMAXINSPECTOR.png)
---

## 🚀 Features
* **Scene Inspector:** Deep dive into object properties, methods, materials, modifiers, and controllers.
* **Class Browser:** Explore all available MaxScript classes categorized by SuperClass or Plugin.
* **Smart Caching:** Fast startup by caching scanned classes into a JSON file.
* **Clipboard Integration:** Double-click any class name to copy it instantly for your scripts.
* **System Info:** Quick access to Viewports, Render Settings, and Graphics Window (GW) properties.

## 🛠 Installation
1.  Ensure you have **3ds Max 2022+** (or any version supporting Python 3 and PySide6).
2.  Copy `3dsMaxInspector.py` to your 3ds Max scripts folder.
3.  Run the script via `Scripting -> Run Script...` or drag and drop it into the viewport.

## 🖥 Usage
* **Refresh Scene:** Updates the tree with current scene objects.
* **Re-Scan All Classes:** Performs a deep scan of all available 3ds Max classes (useful after installing new plugins).
* **Search:** Use the search bar in the "All Classes" tab to quickly find specific classes.

## 🤝 Support & Donation
If you find this tool helpful, consider supporting the development:
* **PayPal:** [![Donate ❤️](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4)

## 📄 License
MIT License - Feel free to use and modify for your professional or personal projects.

**Author:** Iman Shirani  
**Version:** 0.0.1
