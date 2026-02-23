"""
Dependency Manager for PhotoCleaner
====================================

Intelligenter Dependency-Checker mit:
- Auto-Erkennung installierter Bibliotheken (dlib, mediapipe, opencv)
- Systemanalyse (Windows Version, Python Version, GPU Verfügbarkeit)
- Fehlermeldungen mit klaren Lösungsvorschlägen
- Empfehlungsengine: Basierend auf System empfiehlt passende Stages
- User-Space Installation (keine Admin-Rechte erforderlich)
"""

import sys
import platform
import subprocess
import importlib
import importlib.util
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """System-Informationen für Dependency-Empfehlungen"""
    os_name: str
    os_version: str
    python_version: str
    python_executable: str
    is_64bit: bool
    has_gpu: bool
    cpu_cores: int
    has_build_tools: bool  # Für dlib


@dataclass
class DependencyStatus:
    """Status einer einzelnen Dependency"""
    name: str
    installed: bool
    version: Optional[str]
    import_name: str  # z.B. "cv2" für opencv-python
    pip_name: str  # z.B. "opencv-python" für pip install
    required_for_stage: int  # 1, 2, oder 3
    size_mb: int  # Download-Größe
    installation_difficulty: str  # "Einfach", "Mittel", "Schwierig"
    requires_build_tools: bool
    error_message: Optional[str] = None


@dataclass
class InstallationRecommendation:
    """Empfehlung für Installation basierend auf System"""
    recommended_package: str  # "mediapipe" oder "dlib"
    reason: str
    alternative: Optional[str]
    warning: Optional[str]


class DependencyManager:
    """Hauptklasse für Dependency-Management"""
    
    # Bekannte Dependencies mit Metadaten
    KNOWN_DEPENDENCIES = {
        "opencv": DependencyStatus(
            name="OpenCV",
            installed=False,
            version=None,
            import_name="cv2",
            pip_name="opencv-python",
            required_for_stage=1,
            size_mb=50,
            installation_difficulty="Einfach",
            requires_build_tools=False
        ),
        "mediapipe": DependencyStatus(
            name="MediaPipe",
            installed=False,
            version=None,
            import_name="mediapipe",
            pip_name="mediapipe",
            required_for_stage=3,
            size_mb=150,
            installation_difficulty="Einfach",
            requires_build_tools=False
        ),
        "dlib": DependencyStatus(
            name="dlib",
            installed=False,
            version=None,
            import_name="dlib",
            pip_name="dlib",
            required_for_stage=2,
            size_mb=40,
            installation_difficulty="Mittel",
            requires_build_tools=True
        ),
        "numpy": DependencyStatus(
            name="NumPy",
            installed=False,
            version=None,
            import_name="numpy",
            pip_name="numpy",
            required_for_stage=1,
            size_mb=20,
            installation_difficulty="Einfach",
            requires_build_tools=False
        ),
        "pillow": DependencyStatus(
            name="Pillow",
            installed=False,
            version=None,
            import_name="PIL",
            pip_name="pillow",
            required_for_stage=1,
            size_mb=10,
            installation_difficulty="Einfach",
            requires_build_tools=False
        )
    }
    
    def __init__(self):
        self.system_info = self._detect_system()
        self.dependencies = self._check_all_dependencies()
        self.recommendation = self._generate_recommendation()
    
    def _detect_system(self) -> SystemInfo:
        """Detektiere System-Informationen"""
        logger.info("Erkenne System-Konfiguration...")
        
        # Python Info
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        is_64bit = sys.maxsize > 2**32
        
        # OS Info
        os_name = platform.system()
        os_version = platform.version()
        
        # CPU Info
        try:
            import os
            cpu_cores = os.cpu_count() or 1
        except (AttributeError, RuntimeError):
            logger.debug("Failed to get CPU core count", exc_info=True)
            cpu_cores = 1
        
        # GPU Detection (CUDA/OpenCL)
        has_gpu = self._detect_gpu()
        
        # Build Tools Detection (für dlib)
        has_build_tools = self._detect_build_tools()
        
        system = SystemInfo(
            os_name=os_name,
            os_version=os_version,
            python_version=python_version,
            python_executable=sys.executable,
            is_64bit=is_64bit,
            has_gpu=has_gpu,
            cpu_cores=cpu_cores,
            has_build_tools=has_build_tools
        )
        
        logger.info(f"System: {os_name} {os_version}, Python {python_version}, "
                   f"{cpu_cores} CPU Cores, GPU: {has_gpu}, Build Tools: {has_build_tools}")
        
        return system
    
    def _detect_gpu(self) -> bool:
        """Versuche GPU zu detektieren (CUDA oder OpenCL)"""
        # Einfache Heuristik: Prüfe ob CUDA libs vorhanden
        try:
            # Versuche torch zu importieren (falls vorhanden)
            import torch
            return torch.cuda.is_available()
        except ImportError:
            pass
        
        # Alternativ: Prüfe OpenCL
        try:
            import pyopencl
            platforms = pyopencl.get_platforms()
            return len(platforms) > 0
        except ImportError:
            pass
        
        # Fallback: Keine GPU erkannt
        return False
    
    def _detect_build_tools(self) -> bool:
        """Prüfe ob C++ Build Tools installiert sind (für dlib)"""
        if platform.system() != "Windows":
            # Auf Linux/Mac normalerweise vorhanden
            return True
        
        # Auf Windows: Prüfe ob cl.exe (MSVC) vorhanden ist
        try:
            result = subprocess.run(
                ["where", "cl.exe"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            logger.debug("Could not detect build tools", exc_info=True)
            return False
    
    def _check_all_dependencies(self) -> Dict[str, DependencyStatus]:
        """Überprüfe alle bekannten Dependencies"""
        logger.info("Überprüfe installierte Bibliotheken...")
        
        dependencies = {}
        for key, dep_template in self.KNOWN_DEPENDENCIES.items():
            # Kopiere Template
            dep = DependencyStatus(
                name=dep_template.name,
                installed=False,
                version=None,
                import_name=dep_template.import_name,
                pip_name=dep_template.pip_name,
                required_for_stage=dep_template.required_for_stage,
                size_mb=dep_template.size_mb,
                installation_difficulty=dep_template.installation_difficulty,
                requires_build_tools=dep_template.requires_build_tools
            )
            
            # Prüfe Installation
            try:
                module = importlib.import_module(dep.import_name)
                dep.installed = True
                
                # Versuche Version zu ermitteln
                if hasattr(module, "__version__"):
                    dep.version = module.__version__
                elif hasattr(module, "VERSION"):
                    dep.version = module.VERSION
                
                logger.info(f"✓ {dep.name} installiert (Version: {dep.version or 'unbekannt'})")
            except ImportError as e:
                dep.installed = False
                dep.error_message = str(e)
                logger.warning(f"✗ {dep.name} nicht installiert")
            except Exception as e:
                dep.installed = False
                dep.error_message = f"Fehler beim Import: {str(e)}"
                logger.error(f"✗ {dep.name} Fehler: {e}")
            
            dependencies[key] = dep
        
        return dependencies
    
    def _generate_recommendation(self) -> InstallationRecommendation:
        """Generiere Installations-Empfehlung basierend auf System"""
        
        # MediaPipe ist immer die einfachste Option
        if not self.dependencies["mediapipe"].installed:
            recommendation = InstallationRecommendation(
                recommended_package="mediapipe",
                reason="MediaPipe ist einfach zu installieren und bietet die beste Genauigkeit (Stufe 3). "
                       "Keine Build-Tools erforderlich.",
                alternative="dlib" if self.system_info.has_build_tools else None,
                warning=None
            )
        
        # Wenn MediaPipe schon installiert ist, empfehle dlib (falls Build Tools vorhanden)
        elif not self.dependencies["dlib"].installed and self.system_info.has_build_tools:
            recommendation = InstallationRecommendation(
                recommended_package="dlib",
                reason="dlib bietet ausgewogene Genauigkeit (Stufe 2) mit geringerem Ressourcenverbrauch. "
                       "Build-Tools wurden erkannt.",
                alternative=None,
                warning=None
            )
        
        # Wenn Build Tools fehlen, warne vor dlib
        elif not self.dependencies["dlib"].installed and not self.system_info.has_build_tools:
            recommendation = InstallationRecommendation(
                recommended_package="dlib",
                reason="dlib bietet ausgewogene Genauigkeit (Stufe 2).",
                alternative="mediapipe",
                warning="⚠ dlib benötigt C++ Build Tools. Installation kann fehlschlagen. "
                       "MediaPipe ist eine einfachere Alternative."
            )
        
        # Alles installiert
        else:
            recommendation = InstallationRecommendation(
                recommended_package="none",
                reason="Alle erweiterten Funktionen sind bereits installiert.",
                alternative=None,
                warning=None
            )
        
        return recommendation
    
    def get_available_stages(self) -> List[int]:
        """Gib verfügbare Eye Detection Stages zurück"""
        stages = [1]  # Stage 1 (Haar Cascade) ist immer verfügbar mit OpenCV
        
        if self.dependencies["opencv"].installed:
            stages.append(1)  # Bestätigung
        
        if self.dependencies["dlib"].installed:
            stages.append(2)
        
        if self.dependencies["mediapipe"].installed:
            stages.append(3)
        
        return sorted(set(stages))
    
    def get_missing_dependencies_for_stage(self, stage: int) -> List[DependencyStatus]:
        """Gib fehlende Dependencies für eine bestimmte Stage zurück"""
        missing = []
        
        for dep in self.dependencies.values():
            if dep.required_for_stage == stage and not dep.installed:
                missing.append(dep)
        
        return missing
    
    def install_package(self, package_key: str, progress_callback=None) -> Tuple[bool, str]:
        """
        Installiere ein Package via pip (User-Space, keine Admin-Rechte)
        
        Args:
            package_key: Key aus KNOWN_DEPENDENCIES (z.B. "mediapipe")
            progress_callback: Optional callback function(progress: float, message: str)
        
        Returns:
            (success: bool, message: str)
        """
        if package_key not in self.dependencies:
            return False, f"Unbekanntes Package: {package_key}"
        
        dep = self.dependencies[package_key]
        
        if dep.installed:
            return True, f"{dep.name} ist bereits installiert."
        
        # Warnung für dlib ohne Build Tools
        if dep.requires_build_tools and not self.system_info.has_build_tools:
            logger.warning(f"{dep.name} benötigt Build Tools, die nicht erkannt wurden.")
        
        logger.info(f"Installiere {dep.name} ({dep.pip_name})...")
        
        if progress_callback:
            progress_callback(0.1, f"Starte Installation von {dep.name}...")
        
        try:
            # pip install --user (User-Space Installation)
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--upgrade",
                dep.pip_name
            ]
            
            if progress_callback:
                progress_callback(0.2, f"Lade {dep.name} herunter (ca. {dep.size_mb} MB)...")
            
            # Führe Installation aus
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 Minuten Timeout
            )
            
            if progress_callback:
                progress_callback(0.8, f"Überprüfe Installation...")
            
            if result.returncode == 0:
                # Aktualisiere Status
                self.dependencies = self._check_all_dependencies()
                
                if self.dependencies[package_key].installed:
                    if progress_callback:
                        progress_callback(1.0, f"✓ {dep.name} erfolgreich installiert!")
                    
                    logger.info(f"✓ {dep.name} erfolgreich installiert")
                    return True, f"{dep.name} erfolgreich installiert."
                else:
                    error_msg = f"Installation scheinbar erfolgreich, aber {dep.name} kann nicht importiert werden."
                    logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"Installation fehlgeschlagen:\n{result.stderr}"
                logger.error(f"Installation von {dep.name} fehlgeschlagen: {result.stderr}")
                
                if progress_callback:
                    progress_callback(0.0, f"✗ Fehler bei Installation")
                
                return False, error_msg
        
        except subprocess.TimeoutExpired:
            error_msg = "Installation-Timeout (>5 Minuten). Bitte manuell installieren."
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Fehler bei Installation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_installation_command(self, package_key: str) -> str:
        """Gib pip install Command für manuelle Installation zurück"""
        if package_key not in self.dependencies:
            return ""
        
        dep = self.dependencies[package_key]
        return f"{sys.executable} -m pip install --user {dep.pip_name}"
    
    def generate_report(self) -> str:
        """Generiere textbasierten Dependency-Report"""
        lines = []
        lines.append("=" * 60)
        lines.append("PhotoCleaner Dependency-Status")
        lines.append("=" * 60)
        lines.append("")
        
        # System Info
        lines.append("SYSTEM-INFORMATIONEN:")
        lines.append(f"  OS: {self.system_info.os_name} {self.system_info.os_version}")
        lines.append(f"  Python: {self.system_info.python_version} ({'64-bit' if self.system_info.is_64bit else '32-bit'})")
        lines.append(f"  CPU Cores: {self.system_info.cpu_cores}")
        lines.append(f"  GPU: {'✓ Verfügbar' if self.system_info.has_gpu else '✗ Nicht erkannt'}")
        lines.append(f"  Build Tools: {'✓ Verfügbar' if self.system_info.has_build_tools else '✗ Nicht erkannt'}")
        lines.append("")
        
        # Dependencies
        lines.append("INSTALLIERTE BIBLIOTHEKEN:")
        for key, dep in self.dependencies.items():
            status = "✓" if dep.installed else "✗"
            version_str = f"(v{dep.version})" if dep.version else ""
            stage_str = f"[Stufe {dep.required_for_stage}]"
            
            lines.append(f"  {status} {dep.name} {version_str} {stage_str}")
            
            if not dep.installed:
                lines.append(f"      → pip install --user {dep.pip_name}")
                if dep.requires_build_tools and not self.system_info.has_build_tools:
                    lines.append(f"      ⚠ Benötigt Build Tools")
        
        lines.append("")
        
        # Available Stages
        available = self.get_available_stages()
        lines.append(f"VERFÜGBARE EYE-DETECTION STUFEN: {', '.join(map(str, available))}")
        
        # Recommendation
        if self.recommendation.recommended_package != "none":
            lines.append("")
            lines.append("EMPFEHLUNG:")
            lines.append(f"  → {self.recommendation.recommended_package}")
            lines.append(f"  Grund: {self.recommendation.reason}")
            
            if self.recommendation.warning:
                lines.append(f"  {self.recommendation.warning}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Convenience Functions
def get_dependency_manager() -> DependencyManager:
    """Singleton-Pattern für DependencyManager"""
    if not hasattr(get_dependency_manager, "_instance"):
        get_dependency_manager._instance = DependencyManager()
    return get_dependency_manager._instance


def check_stage_availability(stage: int) -> bool:
    """Schnelle Überprüfung ob eine Stage verfügbar ist"""
    manager = get_dependency_manager()
    return stage in manager.get_available_stages()


def get_stage_status_message(stage: int) -> str:
    """Generiere Status-Nachricht für eine Stage (deutsch)"""
    manager = get_dependency_manager()
    available = manager.get_available_stages()
    
    if stage in available:
        return "✓ Bereit"
    
    missing = manager.get_missing_dependencies_for_stage(stage)
    
    if not missing:
        return "✓ Bereit"
    
    # Generiere Fehlermeldung
    dep_names = [dep.name for dep in missing]
    return f"⚠ Benötigt: {', '.join(dep_names)}"


if __name__ == "__main__":
    # Test-Modus: Zeige Dependency-Report
    logging.basicConfig(level=logging.INFO)
    
    manager = DependencyManager()
    print(manager.generate_report())
    
    print("\n\nEMPFEHLUNG:")
    print(f"Package: {manager.recommendation.recommended_package}")
    print(f"Grund: {manager.recommendation.reason}")
    if manager.recommendation.warning:
        print(f"Warnung: {manager.recommendation.warning}")
