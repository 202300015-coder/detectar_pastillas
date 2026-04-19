from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from image_findings import analyze_image, analyze_image_array, _candidate_similarity, AnalysisSettings

def load_references(pills_dir: str = "pills") -> list[dict]:
    """Carga y analiza todas las imagenes de referencia en el directorio de pastillas."""
    pills_path = Path(pills_dir)
    references = []
    print(f"Cargando referencias de {pills_path.absolute()}...")
    
    # Extensiones de imagen soportadas
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    image_files = []
    for ext in extensions:
        image_files.extend(pills_path.glob(ext))
    
    for img_path in image_files:
        try:
            print(f"  Analizando {img_path.name}...", end=" ", flush=True)
            result = analyze_image(img_path)
            if result["candidates"]:
                # Tomamos el candidato mas grande/principal de la imagen de referencia
                ref_candidate = result["candidates"][0]
                ref_candidate["file_name"] = img_path.name
                references.append(ref_candidate)
                print("OK")
            else:
                print("No se detecto pastilla")
        except Exception as e:
            print(f"Error: {e}")
            
    return references

def run_camera_identification(references: list[dict], camera_index: int = 0):
    if not references:
        print("Error: No hay referencias cargadas para comparar.")
        return

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir la camara {camera_index}.")
        return

    print("\n--- Identificador de Pastillas Directo ---")
    print("Controles:")
    print("  's' - Escanear y buscar coincidencia")
    print("  'q' - Salir")
    
    settings = AnalysisSettings()
    last_match = "Ninguna"
    last_score = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        display = frame.copy()
        
        # UI en pantalla
        cv2.putText(display, f"Ultima: {last_match} ({last_score:.2f})", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "s: Escanear | q: Salir", (10, frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        cv2.imshow("Identificador de Pastillas", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        
        if key == ord("s"):
            print("\nEscaneando cuadro de camara...")
            # Analizamos el frame actual
            result = analyze_image_array(frame, "camera_frame", settings=settings)
            
            if not result["candidates"]:
                print("No se detecto ninguna pastilla en el cuadro.")
                last_match = "No detectada"
                last_score = 0.0
                continue
            
            # Comparamos el mejor candidato del frame contra todas nuestras referencias
            camera_candidate = result["candidates"][0]
            
            best_match_name = "Desconocida"
            max_similarity = 0.0
            
            for ref in references:
                sim = _candidate_similarity(camera_candidate, ref)
                if sim > max_similarity:
                    max_similarity = sim
                    best_match_name = ref["file_name"]
            
            last_match = best_match_name
            last_score = max_similarity
            
            print(f"RESULTADO: {best_match_name} (Similitud: {max_similarity:.4f})")
            
            # Mostrar visualmente el hallazgo por un momento
            debug_frame = result["debug_image_bgr"]
            cv2.putText(debug_frame, f"MATCH: {best_match_name}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("Resultado Escaneo", debug_frame)
            cv2.waitKey(2000) # Mostrar resultado por 2 segundos

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 1. Cargar las imagenes de la carpeta 'pills' como base de datos
    refs = load_references("pills")
    
    # 2. Iniciar la camara
    if refs:
        run_camera_identification(refs)
    else:
        print("No se encontraron imagenes validas en 'pills/'. Abortando.")
