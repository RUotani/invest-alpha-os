# Theme Dictionary v1.4

版: 2026-06-06  
目的: fixture/cache-only で銘柄をテーマ・役割へマッピングする。

## テーマ一覧

| ThemeId | 表示名 |
| --- | --- |
| nand_memory | NAND / Memory |
| semiconductor_equipment | Semiconductor Equipment |
| ai_infrastructure | AI Infrastructure |
| data_center_power | Data Center Power |
| nuclear_energy | Nuclear / Energy |
| defense | Defense |
| healthcare | Healthcare |
| gold_precious_metals | Gold / Precious Metals |
| crypto_related | Crypto Related |
| jp_value_financials | Japanese Value / Financials |

## 固定期待: 285A

```text
ticker: 285A
theme: NAND / Memory
role_hint: theme_proxy
not early_discovery
```

## 実装

- `src/invis_alpha_os/discovery/theme_dictionary.py`
- `src/invis_alpha_os/discovery/candidate_roles.py`
