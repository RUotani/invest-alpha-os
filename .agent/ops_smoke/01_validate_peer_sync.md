# Peer sync (cache-only)

- peer_map: `config/peer_map.yaml`
- pairs evaluated: 2

## Summary

- `diverged_peer_outperform`: 2

## Pairs

| anchor | peer | status | spread | corr | aligned |
| --- | --- | --- | --- | --- | --- |
| AAPL | MSFT | diverged_peer_outperform | -5.70% | -0.12 | 69 |
| AAPL | GOOGL | diverged_peer_outperform | -4.35% | 0.16 | 5472 |

### Interpretation

- **AAPL → MSFT**: Peer outperformed anchor by 5.70% over 20d.
- **AAPL → GOOGL**: Peer outperformed anchor by 4.35% over 20d.

## Next commands

- `Add peers in config/peer_map.yaml (anchor → list).`
- `.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown`
- `weekly-us-observation --dry-run  # optional; peer_sync not yet in weekly cycle`

