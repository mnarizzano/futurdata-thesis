import json, shutil
from html import escape
from pathlib import Path
from exporters.renderer import render_main_content, render_sidebar
from exporters.scripts import get_scripts
from exporters.styles import get_styles

class HTMLExporter:
    def export(self, ir_path: str, output_path: str) -> None:
        ir=self._load_ir(ir_path); out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
        self._copy_local_images(ir,Path(ir_path).parent.parent,out.parent)
        out.write_text(self._build_html(ir),encoding='utf-8')
        print(f'HTML wizard exported successfully to: {out}')
    def _load_ir(self,ir_path):
        with Path(ir_path).open(encoding='utf-8') as f:return json.load(f)
    def _copy_local_images(self,ir,root,out):
        paths=set()
        def c(x):
            if isinstance(x,dict):
                im=x.get('image')
                if isinstance(im,dict) and im.get('path') and not im.get('is_url',False):paths.add(im['path'])
        c(ir.get('product',{}))
        for s in ir.get('steps',[]):
            for a in s.get('actions',[]):c(a)
            for o in s.get('outputs',[]):c(o)
            c(s.get('continues_as') or {})
        for p in ir.get('bill_of_materials',[]):c(p)
        for rp in paths:
            src=root/rp; dst=out/rp
            if src.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    def _build_html(self,ir):
        name=escape(ir.get('product',{}).get('name','Disassembly Wizard'))
        data=json.dumps(ir,ensure_ascii=False).replace('</','<\\/')
        return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} — Disassembly Wizard</title><style>{get_styles()}</style></head><body class="welcome-mode"><div class="app">{render_sidebar()}{render_main_content()}</div><script>const ir={data};{get_scripts()}</script></body></html>'''
