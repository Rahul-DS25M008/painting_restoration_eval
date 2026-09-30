"""Copy recorded N29 comparison members and N28 policy rows; no analysis."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.focused_portrait import verified_source
from restoration_eval.case_explorer import INDEX, N29, panel_index


def build():
    package=open_dashboard_package(ROOT)
    rows=[]
    policies=[]
    for pid in package.painting_lookup.painting_id:
        shard=package.load_painting(pid)
        cases={r['case_id']:r for r in shard['cases']}
        for candidate in shard['candidates']:
            for panel in candidate.get('counterfactual_panel_ids',[]):
                family=panel[3:].rsplit('_',1)[0]
                path=f'{N29}/figures/counterfactual_panels/{panel}.png'
                if path not in panel_index():
                    raise ValueError(f'Unregistered comparison panel: {path}')
                row={k:candidate[k] for k in ('candidate_id','case_id','model_id')}
                row.update(painting_id=pid,family=family,panel_path=path)
                case=cases[candidate['case_id']]
                if family in ('metric_subset','evidence_family_removal'):
                    policies.append(row)
                    continue
                if family=='damage_size':
                    value=str(case['target_damage_fraction'])
                    label=f"{float(value)*100:g}% target damage"
                elif family=='mask_placement':
                    value=candidate['case_id'].rsplit('__',1)[-1]
                    label=value.replace('_',' ')
                else:
                    key={'cross_model':'model_id','diffusion_seed':'seed','prompt_policy':'prompt_variant_id'}[family]
                    value=str(candidate[key]);label=value.replace('_',' ')
                rows.append(dict(row,value=value,label=label))
    source='outputs/28_metric_and_region_policy_ablation/metrics/flag_stability.csv'
    path=verified_source(source)
    by_candidate={}
    for row in policies:by_candidate.setdefault(row['candidate_id'],[]).append(row)
    with path.open(encoding='utf-8-sig',newline='') as handle:
        for record in csv.DictReader(handle):
            if record['candidate_id'] not in by_candidate or record['status']!='ok':continue
            scenario=record['scenario_id']
            for item in by_candidate[record['candidate_id']]:
                allowed=(scenario in {'complete_approved_framework','only_classical','only_perceptual','only_semantic_feature'}
                         if item['family']=='metric_subset' else scenario=='complete_approved_framework' or scenario.startswith('without_'))
                if allowed:rows.append(dict(item,value=scenario,label=scenario.replace('_',' '),record=record))
    content={'sources':[{'path':source,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}],
             'scope':'Recorded members of the fourteen N29 selected comparisons; candidate authority is N34.',
             'rows':sorted(rows,key=lambda r:(r['family'],r['value'],r['candidate_id'],r['panel_path']))}
    raw=json.dumps(content,ensure_ascii=False,indent=2).encode('utf-8')
    (INDEX/'choices.json').write_bytes(raw)
    (INDEX/'choices_manifest.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows)},indent=2)+'\n',encoding='utf-8')
    print(f'Copied {len(rows)} saved comparison choices across {len({r["family"] for r in rows})} families')


if __name__=='__main__':build()
