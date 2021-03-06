from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import typer
from datamodel_code_generator import InputFileType, PythonVersion
from datamodel_code_generator import generate as generate_models
from datamodel_code_generator.format import format_code
from jinja2 import Environment, FileSystemLoader

from fastapi_code_generator.parser import OpenAPIParser, Operation, ParsedObject

app = typer.Typer()  # type: ignore

BUILTIN_TEMPLATE_DIR = Path(__file__).parent / "template"


@app.command()
def main(
    input_file: typer.FileText = typer.Option(..., "--input", "-i"),  # type: ignore
    output_dir: Path = typer.Option(..., "--output", "-o"),  # type: ignore
    template_dir: Optional[Path] = typer.Option(None, "--template-dir", "-t"),  # type: ignore
) -> None:
    input_name: str = input_file.name
    input_text: str = input_file.read()
    return generate_code(input_name, input_text, output_dir, template_dir)


def generate_code(
    input_name: str, input_text: str, output_dir: Path, template_dir: Optional[Path]
) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    if not template_dir:
        template_dir = BUILTIN_TEMPLATE_DIR
    parser = OpenAPIParser(input_name, input_text)
    parsed_object: ParsedObject = parser.parse()

    environment: Environment = Environment(
        loader=FileSystemLoader(
            template_dir if template_dir else f"{Path(__file__).parent}/template",
            encoding="utf8",
        ),
    )
    results: Dict[Path, str] = {}
    for target in template_dir.rglob("*"):
        relative_path = target.relative_to(template_dir.absolute())
        result = environment.get_template(str(relative_path)).render(
            operations=parsed_object.operations, imports=parsed_object.imports
        )
        results[relative_path] = format_code(result, PythonVersion.PY_38)

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = f"""\
# generated by fastapi-codegen:
#   filename:  {Path(input_name).name}
#   timestamp: {timestamp}"""

    for path, code in results.items():
        with output_dir.joinpath(path.with_suffix(".py")).open("wt") as file:
            print(header, file=file)
            print("", file=file)
            print(code.rstrip(), file=file)

    generate_models(
        input_name=input_name,
        input_text=input_text,
        input_file_type=InputFileType.OpenAPI,
        output=output_dir.joinpath("models.py"),
        target_python_version=PythonVersion.PY_38,
    )


if __name__ == "__main__":
    typer.run(main)  # type: ignore
