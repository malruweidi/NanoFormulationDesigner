# Carrier Recommender

`nanoform.carrier_recommender.recommend_carriers(...)` ranks solid carriers,
cryo/lyoprotectants, and dispersibility aids for a route/family/process. It is a
transparent heuristic aid.

## Logic
- **Lyophilization / freeze-drying:** favors glass formers; score rises with Tg
  (trehalose > sucrose > mannitol for cake stability). Non-cryoprotectants score low.
- **Dry powder / spray drying / pulmonary:** favors porous/dispersibility aids
  (colloidal silica, MCC) and known DPI carriers (leucine, lactose).
- **Parenteral:** insoluble solids (MCC, colloidal silica) are penalized and
  warned; parenteral-grade complexation hosts (SBE-β-CD) are noted for other routes.

## Score
```
powder route:  0.55*dpi_fit + 0.45*lyo_fit
otherwise:     0.80*lyo_fit + 0.20*dpi_fit
```

## Example
```bash
python -m nanoform.cli recommend-carrier --route pulmonary --family dry_powder_carrier
```
```python
from nanoform.carrier_recommender import recommend_carriers
recommend_carriers(route="parenteral", family="liposome", process="lyophilization")
```

## Caveats
Cryoprotectant:drug/lipid ratio, annealing, and residual moisture are not
modeled — these are decided in the lab. The recommender narrows candidates; it
does not set a protocol.
