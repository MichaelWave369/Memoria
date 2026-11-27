// Offline fixture relation admission; no verified identities or runtime authority.
export function resolveRelation(records, request, withdrawn){
 const label=x=>typeof x==="string"&&/^[a-z0-9][a-z0-9._:-]{0,63}$/.test(x);
 const epoch=x=>Number.isSafeInteger(x)&&x>=0;
 const exact=(x,keys)=>x!==null&&typeof x==="object"&&!Array.isArray(x)&&Object.keys(x).sort().join(",")===keys.slice().sort().join(",");
 if(!exact(request,["alias","app","context","now"])||![request.alias,request.app,request.context].every(label)||!epoch(request.now))throw new TypeError("invalid fixture request");
 if(!Array.isArray(records)||records.length>128||!Array.isArray(withdrawn)||withdrawn.length>128||!withdrawn.every(label)||new Set(withdrawn).size!==withdrawn.length)throw new TypeError("invalid fixture ledger");
 const ids=new Set();
 for(const r of records){
  if(!exact(r,["id","alias","target","app","context","source","root","review","state","issued","expires"])||
    ![r.id,r.alias,r.target,r.app,r.context,r.source,r.root].every(label)||
    !["approved","pending","rejected"].includes(r.review)||!["active","retired"].includes(r.state)||
    !epoch(r.issued)||!epoch(r.expires)||r.expires<=r.issued||ids.has(r.id))throw new TypeError("invalid relation record");
  ids.add(r.id);
 }
 const relevant=records.filter(r=>r.alias===request.alias&&r.app===request.app&&r.context===request.context);
 const active=relevant.filter(r=>r.state==="active"&&r.review==="approved"&&r.issued<=request.now&&request.now<r.expires&&!withdrawn.includes(r.id)&&!withdrawn.includes(r.root)&&!withdrawn.includes(r.source));
 const roots=new Set(active.map(r=>r.root)), targets=new Set(active.map(r=>r.target));
 const sources=new Set(active.map(r=>r.source));
 const result=(target,reason)=>({target,reason,approved_records:active.length,distinct_roots:roots.size,distinct_sources:sources.size,authority:"NONE"});
 if(!relevant.length)return result(null,"NO_SCOPE");
 if(!active.length)return result(null,"NO_CURRENT_EVIDENCE");
 if(targets.size!==1)return result(null,"CONFLICT");
 // Two distinct source/root pairs with no shared source or root. Counts alone
 // do not establish independence or prevent fabricated provenance.
 if(!active.some(a=>active.some(b=>a.root!==b.root&&a.source!==b.source)))return result(null,"INSUFFICIENT_DISTINCT_EVIDENCE");
 return result(active[0].target,"SUPPORTED_FIXTURE");
}
export function evaluate(f,resolve){
 const rows=f.scenarios.map(s=>({id:s.id,expected:s.expected,truth:s.truth,...resolve(s.records,s.request,s.withdrawn)}));
 return {schema:"memoria-relation-provenance-result/v1",synthetic:true,authority:"NONE",summary:{scenarios:rows.length,contract_matches:rows.filter(r=>r.target===r.expected).length,admitted:rows.filter(r=>r.target!==null).length,correct_admissions:rows.filter(r=>r.target!==null&&r.target===r.truth).length,wrong_admissions:rows.filter(r=>r.target!==null&&r.target!==r.truth).length,abstentions:rows.filter(r=>r.target===null).length},rows};
}
