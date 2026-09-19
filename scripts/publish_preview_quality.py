"""Publish a fully verified rebuild, retaining the entire previous export."""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_main_preview import main as build_preview


def main():
    output=(ROOT/'output').resolve()
    live=output/'universal'
    stage=output/'universal-512-staging'
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    previous_size=json.loads((live/'sprites.json').read_text())['frameSize'][0]
    archive=output/(f'universal-{previous_size}-'+stamp)
    for path in (live,stage,archive):
        assert path.resolve().parent==output and not path.is_symlink(),path
    assert live.is_dir() and stage.is_dir() and not archive.exists()
    validation=json.loads((stage/'validation.json').read_text())
    snapshot=json.loads((stage/'rebuild-input.json').read_text())
    assert validation['status']=='passed'
    assert validation['inputSignature']==snapshot['signature']
    assert hashlib.sha256((stage/'review-sprites.json').read_bytes()).hexdigest()==validation['manifestSha256']
    # Avoid publishing a stale snapshot over edits made during the long batch.
    for group in snapshot['groups']:
        config_path=ROOT/'config'/group['configName']
        current=json.loads(config_path.read_text(encoding='utf-8'))
        changed={key for key in current.keys()|group['config'].keys() if current.get(key)!=group['config'].get(key)}
        # Display labels do not affect the frozen poses, camera or rendered pixels.
        # Preserve a label correction made while the batch was running.
        assert changed <= {'display_name'},f'Render config changed during rebuild: {config_path}: {changed}'
        assert hashlib.sha256((ROOT/group['config']['asset']).read_bytes()).hexdigest()==group['assetSha256'],f'Asset changed during rebuild: {group["configName"]}'
    live.rename(archive)
    try:
        stage.rename(live)
    except Exception:
        archive.rename(live)
        raise
    for group in snapshot['groups']:
        config_path=ROOT/'config'/group['configName']
        cfg=json.loads(config_path.read_text(encoding='utf-8'))
        cfg.update(snapshot['quality'])
        cfg.update({'render_device':'OPTIX','denoising_gpu':True})
        if group['folder']=='teeter':
            manifest=json.loads((live/'teeter/sprites.json').read_text())
            clip=manifest['animations']['teeter']
            cfg['animations'][0]['platform_edge']=clip['platformEdge']
            cfg['animations'][0]['note']=clip['reviewNote']
        config_path.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    profile_path=ROOT/'config/quality-approved.json'
    profile=json.loads(profile_path.read_text())
    profile['rollout']='Applied to all main-preview Base and Edited clips; independent study and custom-character exports remain separate.'
    profile['render_settings'].update({'render_device':'OPTIX','denoising_gpu':True})
    profile_path.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
    comparison_path=live/'quality-lab/comparison.json'
    comparison=json.loads(comparison_path.read_text())
    comparison['baselineArchive']=archive.relative_to(ROOT).as_posix()
    comparison_path.write_text(json.dumps(comparison,indent=2))
    report={**validation,'archive':str(archive),'publishedAt':stamp}
    build_preview()
    report['publishedManifestSha256']=hashlib.sha256((live/'review-sprites.json').read_bytes()).hexdigest()
    (live/'quality-rollout.json').write_text(json.dumps(report,indent=2))
    print('HQ_PUBLISHED',json.dumps(report),flush=True)


if __name__=='__main__':
    main()
