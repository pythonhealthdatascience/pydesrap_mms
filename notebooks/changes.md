## Added

* `analysis.ipynb`: Added `create_user_controlled_hist` to allow users to decide the KPI histogram to view.

## Changed

*  `analysis.ipynb`: modified `plot_results_spread` to accept `DataFrame` parameter containing results rather than using a variable with notebook scope.
* `environment.yaml`: patched to include channel. It now installs correctly
* `environment.yaml`: added `nbqa` and `black` to auto-format notebooks.