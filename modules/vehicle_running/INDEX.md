# modules/vehicle_running/  (summary: odometer readings and service estimates beside Vehicles, files only; built on Lane B's draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Vehicles (vehicles and services) and People (providers) | changing the module's details |
| tables.toml | Odometer readings with their gentle lower and mixed-unit checks and dots chart, `bring_in` for earlier readings (0137), and service estimates with private amount and scope | adding a field or a check |
| labels.toml | Friendly labels, help, form and list order, Add a reading, and the Cost estimates list on a service's page | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |
