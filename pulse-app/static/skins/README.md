# Pulse domain skins

The report shell loads the basic skin from `default.css`. Operator edits in
Sources & Settings are saved as one CSS file per domain in the persistent
`/data/audit/skins` directory (next to the research database):

```text
/data/audit/skins/<domain>.css
```

For example, `purpledogwalkers.com.css` applies to that domain's operator
dashboard and client report when Custom CSS is selected. The selected mode is
kept in a companion JSON file. Domain files can override semantic variables
(`--skin-brand`, `--skin-brand-strong`, `--skin-workspace`, and so on) and
small layout rules only; report data and templates remain shared.
