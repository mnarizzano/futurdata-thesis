"""Exercise the exported JavaScript with image and image-free components."""
import shutil
import subprocess

import pytest

from src.main.services.html_exporter.scripts import get_scripts


def test_input_images_and_compact_part_cards_preserve_grading():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed to exercise the HTML renderer")
    harness = r"""
const assert=require('node:assert/strict');
const elements={};
const document={
  getElementById(id){
    return elements[id]??=( {
      innerHTML:'', textContent:'',
      classList:{values:new Set(),toggle(k,on){on?this.values.add(k):this.values.delete(k)}}
    });
  }
};
const localStorage={setItem(){}};
const ir={product:{name:'Unrelated product',image:{path:'product.png'}},steps:[]};
"""
    checks = r"""
const root={input:{name:'Root & assembly',image:{path:'root.png'}},operation:'Diamond',
            image:{path:'operation.png'},actions:[{image:{path:'action.png'}}]};
renderImage(root);
assert.equal(elements.startingAssembly.textContent,'Root & assembly');
assert.match(elements.imageBox.innerHTML,/root.png/);
assert.match(elements.imageBox.innerHTML,/alt="Root &amp; assembly"/);
assert.doesNotMatch(elements.imageBox.innerHTML,/operation.png|action.png|product.png/);
assert.equal(elements.stepLayout.classList.values.has('no-assembly-image'),false);
// Jump to another branch directly: its own input wins over any preceding output.
renderImage({...root,input:{name:'Other branch'}});
assert.equal(elements.startingAssembly.textContent,'Other branch');
assert.equal(elements.imageBox.innerHTML,'');
assert.equal(elements.stepLayout.classList.values.has('no-assembly-image'),true);
renderImage(root);
assert.equal(elements.stepLayout.classList.values.has('no-assembly-image'),false);
const parts=[{node_id:'screws',name:'2 Screws',weight:10,weight_unit:'g',material:'Steel',color:'Metallic'},
             {node_id:'plate',name:'Top plate',image:{path:'plate.png'}}];
renderOutputs(parts);
let cards=elements.outputsList.innerHTML.split('<article class="part-card">').slice(1);
assert.doesNotMatch(cards[0],/<img|No image|image-placeholder/);
assert.match(cards[0],/2 Screws/);
assert.match(cards[0],/Steel/);
assert.match(cards[0],/<select/);
assert.match(cards[0],/type="number"/);
assert.match(cards[1],/plate.png/);
updatePart('screws','quality','Working');
updatePart('screws','measured','9.5');
renderOutputs(parts);
assert.match(elements.outputsList.innerHTML, /option selected>Working/);
assert.match(elements.outputsList.innerHTML, /value="9.5"/);
renderContinues([{name:'Remaining housing'}]);
assert.match(elements.continuesAs.innerHTML,/Remaining assembly after this step/);
assert.match(elements.continuesAs.innerHTML,/Remaining housing/);
"""
    # Suppress startup; this harness supplies only the DOM used by the renderers.
    scripts = get_scripts().split("document.addEventListener('keydown'")[0]
    result = subprocess.run([node, "-"], input=harness + scripts + checks,
                            text=True, encoding="utf-8", capture_output=True)
    assert result.returncode == 0, result.stderr

