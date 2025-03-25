# runex/cli.py
import click
from runex.core import generate_prompt

@click.command()
@click.argument('root_dir', type=click.Path(exists=True, file_okay=False))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('--casefold', '-c', is_flag=True, help="Enable case-insensitive matching")
@click.option('--json', '-oj', 'json_mode', is_flag=True, help="Output JSON instead of text")
@click.option('--only-structure', '-s', is_flag=True, help="Omit file contents in the output")
@click.option('--relative-root', '-rr', is_flag=True, help="Force the root directory name to be '.' instead of the basename")
def main(root_dir, output_file, casefold, json_mode, only_structure, relative_root):
    """
    Generates a representation of a project directory and file structure following .gitignore rules.
    """
    display_actual_root = not relative_root
    prompt = generate_prompt(
        root_dir=root_dir,
        casefold=casefold,
        json_mode=json_mode,
        only_structure=only_structure,
        display_actual_root=display_actual_root
    )
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        click.echo(f"Output written to {output_file}")
    else:
        click.echo(prompt)

if __name__ == '__main__':
    main()
