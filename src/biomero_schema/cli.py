"""CLI for biomero schema validation and parsing."""
import json
import os.path
import sys
from typing import Any, Dict
import yaml

import click
import jsonschema
from rich.console import Console
from rich.pretty import pprint

from biomero_schema.adapters import detect_schema_format, parse_descriptor
from biomero_schema.models import WorkflowSchema

console = Console()


def load_descriptor_file(file_path: str) -> Dict[str, Any]:
    """Load descriptor file and return parsed content."""
    try:
        ext = os.path.splitext(file_path)[1]
        with open(file_path) as f:
            if ext in (".yaml", ".yml"):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: File '{file_path}' not found[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in '{file_path}': {e}[/red]")
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Schema validator CLI tool."""
    pass

@cli.command()
def schema():
    """Print JSON schema representation of pydantic model"""
    model_schema = WorkflowSchema.model_json_schema()
    console.print(json.dumps(model_schema, indent=2))


@cli.command()
@click.argument("descriptor_file", type=click.Path(exists=True))
def validate(descriptor_file: str):
    """Validate a descriptor file against the JSON schema.

    BIAFLOWS and BILAYERS descriptors are converted to biomero-schema first.
    """
    console.print(f"[blue]Validating {descriptor_file}...[/blue]")

    # Load schema and descriptor file
    schema = WorkflowSchema.model_json_schema()
    data = load_descriptor_file(descriptor_file)

    try:
        schema_format = detect_schema_format(data)
        if schema_format != "biomero-schema":
            console.print(f"[blue]Converting {schema_format} descriptor to biomero-schema...[/blue]")
            data = parse_descriptor(data).model_dump(mode="json", by_alias=True, exclude_none=True)
        jsonschema.validate(data, schema)
        console.print("[green]✓ Validation successful![/green]")
    except jsonschema.ValidationError as e:
        console.print("[red]✗ Validation failed:[/red]")
        console.print(f"[red]  {e.message}[/red]")
        if e.absolute_path:
            console.print(f"[yellow]  Path: {' -> '.join(str(p) for p in e.absolute_path)}[/yellow]")
        sys.exit(1)
    except jsonschema.SchemaError as e:
        console.print(f"[red]Error: Invalid schema: {e.message}[/red]")
        sys.exit(1)
    except ValueError as e:
        # Unknown format, or conversion failed (pydantic ValidationError is a ValueError)
        console.print("[red]✗ Validation failed:[/red]")
        console.print(f"[red]  {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("descriptor_file", type=click.Path(exists=True))
@click.option("--pretty", is_flag=True, help="Pretty print the parsed object")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def parse(descriptor_file: str, pretty: bool, output_json: bool):
    """Parse a descriptor file into a Pydantic representation."""
    # Keep stdout clean for --json so the output can be redirected to a file
    status = Console(stderr=True) if output_json else console
    status.print(f"[blue]Parsing {descriptor_file}...[/blue]")
    
    # Load and validate descriptor file
    data = load_descriptor_file(descriptor_file)
    
    try:
        # Detect format and parse into Pydantic model
        workflow = parse_descriptor(data, name=descriptor_file)
        
        status.print("[green]✓ Parsing successful![/green]")
        
        if output_json:
            # Output as JSON
            json_output = workflow.model_dump_json(indent=2, by_alias=True)
            # Plain echo: rich would wrap long strings and break the JSON
            click.echo(json_output)
        elif pretty:
            # Pretty print the Pydantic object
            console.print("\n[bold]Parsed Workflow Object:[/bold]")
            pprint(workflow)
        else:
            # Default: show structured representation
            console.print("\n[bold]Workflow Schema:[/bold]")
            console.print(f"Name: {workflow.name}")
            console.print(f"Description: {workflow.description}")
            console.print(f"Schema Version: {workflow.schema_version}")
            console.print(f"Problem Class: {workflow.problem_class}")
            console.print(f"Container Image: {workflow.container_image.image} ({workflow.container_image.type})")
            console.print(f"Citations: {len(workflow.citations)} citation(s)")
            console.print(f"Inputs: {len(workflow.inputs)} parameter(s)")
            console.print(f"Outputs: {len(workflow.outputs)} parameter(s)")
            console.print(f"Authors: {len(workflow.authors)} author(s)")
            console.print(f"Institutions: {len(workflow.institutions)} institution(s)")
            
    except Exception as e:
        status.print(f"[red]✗ Parsing failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
