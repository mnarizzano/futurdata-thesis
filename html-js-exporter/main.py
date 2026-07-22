from exporters.html_exporter import HTMLExporter


def main():
    exporter = HTMLExporter()
    exporter.export(
        ir_path="data/ir_output.json",
        output_path="output/wizard.html"
    )


if __name__ == "__main__":
    main()