# Formulation Families

Each family maps to a canonical membrane/matrix logic. The wizard seeds a
starting template (`nanoform/guided.py`) and sanity checks enforce minimum
requirements (`nanoform/sanity.py`).

| Family | Core materials | Key descriptors | Typical failure modes |
|---|---|---|---|
| **niosome** | nonionic surfactant + cholesterol (± charge inducer) | CPP, mixed HLB, rigidity | leakage, aggregation, micellization if HLB too high |
| **proniosome** | surfactant + carrier (dry) → hydrate to niosome | CPP, carrier fit | poor reconstitution |
| **liposome** | phospholipid + cholesterol (± PEG-lipid) | Tm, rigidity, PEG fraction | leakage, oxidation, fast clearance (no PEG) |
| **transfersome** | phospholipid + edge activator | edge-activator fraction, deformability | rigid membrane → no deformability |
| **ethosome** | phospholipid + high ethanol | ethanol content, fluidity | insufficient ethanol; instability |
| **bilosome** | surfactant/lipid + bile salt | bile-salt fraction | over-lysis at high bile salt |
| **lipid nanoparticle (LNP)** | ionizable lipid + helper PC + cholesterol + PEG-lipid | ionizable fraction, apparent pKa | poor encapsulation / endosomal escape |
| **SLN** | solid lipid + surfactant | crystallinity, Tm | drug expulsion on crystallization |
| **NLC** | solid + liquid lipid + surfactant | crystallinity (lowered), loading | still some expulsion; oil leakage |
| **nanoemulsion** | oil + surfactant (± co-surfactant) | HLB, droplet packing | Ostwald ripening, creaming |
| **polymeric NP** | polymer + stabilizer | χ (drug–polymer), Tg | burst release, aggregation |
| **lipid–polymer hybrid** | polymer core + lipid/PEG shell | χ, PEG fraction | incomplete shell, complexity cost |
| **dry-powder carrier** | matrix + carrier/dispersibility aid | carrier fit, aerodynamic size | poor dispersibility, moisture uptake |

## Route notes
- **Oral:** bile/enzyme destabilization of plain vesicles → bilosomes/coatings.
- **Pulmonary:** aerodynamic size (~1–5 µm) and device stress dominate over DLS
  size; add leucine; verify post-nebulization integrity.
- **Parenteral:** sterility, endotoxin, isotonicity, hemocompatibility; prefer
  GRAS/class-3 solvents; justify any cationic surface.
- **Topical/transdermal:** deformable/penetration-enhancing systems usually beat
  rigid vesicles.

## Nucleic-acid / gene delivery
LNPs and polyplexes are **delivery-chain** problems: protect the cargo → reach
the tissue → enter cells → escape the endosome → unpack → produce the biological
effect, all with acceptable innate-immune/toxicity burden. Particle formation
and uptake are necessary but not sufficient.
