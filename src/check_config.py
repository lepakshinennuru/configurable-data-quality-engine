
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"


def main():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    print("Configuration loaded successfully!")
    print("\nDatasets:")

    for dataset_name in config["datasets"]:
        print(f"- {dataset_name}")

    print("\nConfigured rules:")

    for rule in config["rules"]:
        print(
            f'{rule["rule_id"]}: '
            f'{rule["type"]} '
            f'({rule["severity"]})'
        )

    print(f'\nTotal rules: {len(config["rules"])}')


if __name__ == "__main__":
    main()
