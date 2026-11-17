from pathlib import Path
import re,sys
R=Path(__file__).resolve().parent.parent;src=Path(sys.argv[1]) if len(sys.argv)>1 else R/'source/game.html';out=Path(sys.argv[2]) if len(sys.argv)>2 else R/'musou.html'
s=src.read_bytes().decode('utf8');assert 'MUSOU_EDITION_1118' not in s
def change(a,b):
 global s
 assert s.count(a)==1,a;s=s.replace(a,b,1)
change('function scnHas(n){return !!SCK[n]', 'function scnHas(n){return Number(n)!==1&&!!SCK[n]')
change('function setScn(n){SCN=scnHas(n)?n:1;', 'function setScn(n){SCN=scnHas(n)?Number(n):2;')
for key in ['save','scn','best','easy']:s=s.replace("'dragon_"+key+"'","'dragon_musou_"+key+"_v1'")
head='''<!-- MUSOU_EDITION_1118 -->
<script>/* Preserve the original save; migrate only an existing non-story campaign. */
try{const n=Number(localStorage.getItem('dragon_scn')||1);if(n>=2&&n<=12&&!localStorage.getItem('dragon_musou_migrated_v1')){for(const key of ['save','scn','best','easy']){const old=localStorage.getItem('dragon_'+key),next='dragon_musou_'+key+'_v1';if(old!==null&&localStorage.getItem(next)===null)localStorage.setItem(next,old);}localStorage.setItem('dragon_musou_migrated_v1','1');}}catch(_){}
</script><style>#musouEntryLink{text-decoration:none;text-align:center}#select .select-menu{flex-wrap:wrap}</style>
'''
change('<head>','<head>'+head)
s=re.sub(r'<title>.*?</title>','<title>無双編｜俺がドラゴン。</title>',s,count=1,flags=re.S)
foot='''<script>/* MUSOU_ENTRY_1118 */
const musouEntryLink=document.createElement('a');musouEntryLink.id='musouEntryLink';musouEntryLink.href='index.html';musouEntryLink.className='btn sm';musouEntryLink.textContent='本編・無双編の入口へ';document.querySelector('.select-menu')?.appendChild(musouEntryLink);
</script>'''
change('</body>',foot+'</body>');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(s.encode('utf8'));print(out)
