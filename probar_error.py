"""Comprueba que un CSV con tensión inválida se rechaza de forma explícita."""
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from procesar import procesar


def main():
    raiz = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix="prueba_error_", dir=raiz) as temporal:
        carpeta = Path(temporal)
        copyfile(raiz / "datos_simulados" / "ensayos.csv", carpeta / "ensayos.csv")
        copyfile(raiz / "datos_simulados" / "mediciones_con_error.csv", carpeta / "mediciones.csv")
        try:
            procesar(carpeta, carpeta / "salida")
        except ValueError as error:
            if "tension_v debe ser numérico" not in str(error):
                raise
            print(f"Error detectado correctamente: {error}")
            print("PRUEBA SUPERADA: el archivo inválido fue rechazado.")
        else:
            raise RuntimeError("PRUEBA FALLIDA: se aceptó un archivo inválido")


if __name__ == "__main__":
    main()
