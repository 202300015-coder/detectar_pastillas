from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2

from image_findings import (
    analyze_image,
    calibrate_frame_against_reference,
    write_camera_calibration_report,
    write_findings_report,
)


class FindingsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Calibracion de Pastillas")
        self.root.geometry("860x620")

        self.selected_files: list[str] = []
        self.reference_path = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value="reports")
        self.camera_index = tk.StringVar(value="0")
        self.status_text = tk.StringVar(
            value="Selecciona una referencia y usa la camara para medir que umbrales detectan mejor."
        )

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(container, text="Calibracion con Camara y Referencia", font=("Segoe UI", 16, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            container,
            text="Modo principal: apunta la camara a una foto impresa y guarda que valores separan mejor la pastilla.",
        )
        subtitle.pack(anchor=tk.W, pady=(4, 14))

        top = ttk.Frame(container)
        top.pack(fill=tk.X, pady=(0, 10))

        ref_frame = ttk.LabelFrame(top, text="Referencia", padding=10)
        ref_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Entry(ref_frame, textvariable=self.reference_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ref_frame, text="Elegir", command=self.select_reference).pack(side=tk.LEFT, padx=(8, 0))

        cam_frame = ttk.LabelFrame(container, text="Camara", padding=10)
        cam_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(cam_frame, text="Indice").pack(side=tk.LEFT)
        ttk.Entry(cam_frame, textvariable=self.camera_index, width=6).pack(side=tk.LEFT, padx=(6, 12))
        ttk.Button(cam_frame, text="Iniciar calibracion", command=self.run_camera_calibration).pack(side=tk.LEFT)

        output_frame = ttk.LabelFrame(container, text="Carpeta de salida", padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(output_frame, textvariable=self.output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Elegir", command=self.select_output_dir).pack(side=tk.LEFT, padx=(8, 0))

        batch_frame = ttk.LabelFrame(container, text="Analisis por imagen", padding=10)
        batch_frame.pack(fill=tk.BOTH, expand=True)

        batch_controls = ttk.Frame(batch_frame)
        batch_controls.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(batch_controls, text="Seleccionar imagenes", command=self.select_files).pack(side=tk.LEFT)
        ttk.Button(batch_controls, text="Limpiar lista", command=self.clear_files).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(batch_controls, text="Procesar imagenes", command=self.process_files).pack(side=tk.RIGHT)

        self.file_list = tk.Listbox(batch_frame, height=16)
        self.file_list.pack(fill=tk.BOTH, expand=True)

        status_frame = ttk.LabelFrame(container, text="Estado", padding=10)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(status_frame, textvariable=self.status_text).pack(anchor=tk.W)

    def select_reference(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecciona imagen de referencia",
            filetypes=[("Imagenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")],
        )
        if file_path:
            self.reference_path.set(file_path)
            self.status_text.set(f"Referencia cargada: {Path(file_path).name}")

    def select_files(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Selecciona imagenes",
            filetypes=[("Imagenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")],
        )
        if not file_paths:
            return
        for file_path in file_paths:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                self.file_list.insert(tk.END, file_path)
        self.status_text.set(f"Imagenes cargadas: {len(self.selected_files)}")

    def clear_files(self) -> None:
        self.selected_files.clear()
        self.file_list.delete(0, tk.END)
        self.status_text.set("Lista limpia.")

    def select_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona carpeta de salida")
        if folder:
            self.output_dir.set(folder)

    def process_files(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("Sin imagenes", "Selecciona al menos una imagen.")
            return

        run_dir = Path(self.output_dir.get()) / datetime.now().strftime("%Y%m%d_%H%M%S_batch")
        results = []
        failures: list[str] = []

        for index, file_path in enumerate(self.selected_files, start=1):
            self.status_text.set(f"Procesando {index}/{len(self.selected_files)}: {Path(file_path).name}")
            self.root.update_idletasks()
            try:
                results.append(analyze_image(file_path))
            except Exception as exc:
                failures.append(f"{Path(file_path).name}: {exc}")

        paths = write_findings_report(results, run_dir)
        message = f"CSV: {paths['csv']}\nJSON: {paths['json']}\nDebug: {paths['debug_dir']}"
        if failures:
            message += "\n\nErrores:\n" + "\n".join(failures[:10])
        self.status_text.set(f"Lote terminado en {run_dir}")
        messagebox.showinfo("Hallazgos generados", message)

    def run_camera_calibration(self) -> None:
        reference = self.reference_path.get().strip()
        if not reference:
            messagebox.showwarning("Sin referencia", "Selecciona una imagen de referencia primero.")
            return

        try:
            camera_index = int(self.camera_index.get().strip() or "0")
        except ValueError:
            messagebox.showwarning("Indice invalido", "El indice de camara debe ser un numero entero.")
            return

        output_dir = Path(self.output_dir.get()) / datetime.now().strftime("%Y%m%d_%H%M%S_camera")
        output_dir.mkdir(parents=True, exist_ok=True)
        session_rows: list[dict[str, object]] = []

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            messagebox.showerror("Camara", f"No se pudo abrir la camara {camera_index}.")
            return

        self.status_text.set("Camara activa. q = salir, s = muestrear y guardar mejores umbrales.")
        sample_index = 0

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue

                display = frame.copy()
                cv2.putText(
                    display,
                    "q = salir | s = muestrear calibracion",
                    (12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Calibracion de Camara", display)
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

                if key == ord("s"):
                    sample_index += 1
                    sample_name = f"sample_{sample_index:03d}"
                    self.status_text.set(f"Analizando muestra {sample_index}...")
                    self.root.update_idletasks()

                    calibration = calibrate_frame_against_reference(reference, frame, frame_name=sample_name)
                    best_trial = calibration["best_trial"]
                    analysis = best_trial["analysis"]

                    overlay_path = output_dir / f"{sample_name}_overlay.png"
                    mask_path = output_dir / f"{sample_name}_mask.png"
                    frame_path = output_dir / f"{sample_name}_frame.png"

                    cv2.imwrite(str(frame_path), frame)
                    cv2.imwrite(str(overlay_path), analysis["debug_image_bgr"])
                    cv2.imwrite(str(mask_path), analysis["mask_candidates"])

                    session_rows.append(
                        {
                            "sample": sample_name,
                            "reference": Path(reference).name,
                            "camera_index": camera_index,
                            "candidate_count": analysis["candidate_count"],
                            "best_score": best_trial["final_score"],
                            "best_similarity": best_trial["best_similarity"],
                            "white_l_min": best_trial["settings"]["white_l_min"],
                            "white_sat_max": best_trial["settings"]["white_sat_max"],
                            "distance_thresholds": ",".join(str(x) for x in best_trial["settings"]["distance_thresholds"]),
                            "min_fill_ratio": best_trial["settings"]["min_fill_ratio"],
                            "min_solidity": best_trial["settings"]["min_solidity"],
                            "best_candidate_color": (
                                best_trial["best_candidate"]["dominant_color"] if best_trial["best_candidate"] else "NONE"
                            ),
                            "best_candidate_aspect_ratio": (
                                best_trial["best_candidate"]["aspect_ratio"] if best_trial["best_candidate"] else 0.0
                            ),
                            "frame_path": str(frame_path),
                            "overlay_path": str(overlay_path),
                            "mask_path": str(mask_path),
                        }
                    )
                    write_camera_calibration_report(session_rows, output_dir)
                    self.status_text.set(
                        f"Muestra {sample_index} guardada. Mejor score={best_trial['final_score']:.3f} en {output_dir}"
                    )
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if session_rows:
            paths = write_camera_calibration_report(session_rows, output_dir)
            messagebox.showinfo(
                "Calibracion guardada",
                f"CSV: {paths['csv']}\nJSON: {paths['json']}\nCarpeta: {output_dir}",
            )
        else:
            messagebox.showinfo("Calibracion", "Sesion cerrada sin muestras guardadas.")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    FindingsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
