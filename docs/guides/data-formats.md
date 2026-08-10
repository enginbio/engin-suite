# Data formats and conventions

```{warning}
Not yet written. The ingest layer and convention are under construction.
```

Engin introduces **no bespoke data container**. Time-series runs are
[xarray](https://docs.xarray.dev/) Datasets; endpoint design-of-experiments data
is a pandas DataFrame. Your data is not locked inside Engin, and there is no new
type to learn.

Will cover: the documented convention over those structures — dimension and
coordinate names, unit attributes, metadata attachment points — and loaders for
the formats teams already hold.
