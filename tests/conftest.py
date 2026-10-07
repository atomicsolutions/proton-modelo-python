def pytest_addoption(parser):
    # O runner do Proton chama:
    #   uv run pytest tests/test_proton_script.py::test_run_proton_execution --id_dataset_run=<id>
    # Sem registrar a opção, o pytest recusaria o argumento.
    parser.addoption("--id_dataset_run", default=None, help="Id da execução no Proton (o runner informa).")
