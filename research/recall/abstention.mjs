// Offline synthetic experiment; no runtime integration.
export function evaluate(fixture){
 const toks=s=>[...new Set(s.toLowerCase().match(/[a-z0-9]+/g)||[])];
 const grid=[];for(const coverage of [0.5,0.75,1])for(const margin of [0,0.125,0.25])for(const minSupported of [1,2])grid.push({coverage,margin,minSupported});
 const round=x=>Number(x.toFixed(12));
 function run(split,mode,gate){
  const docs=split.documents.map(d=>({id:d.id,words:new Set(toks(d.text))}));
  const rows=[];let comparisons=0,probes=0,lookups=0;
  for(const q of split.queries){
   const words=toks(q.text), mapping=words.map(w=>{if(mode==="direct")return [w];lookups++;return [w,...(split.relations[w]||[])];});
   const ambiguous=mode!=="direct"&&words.some(w=>(split.relations[w]||[]).length>1);
   const expanded=new Set(mapping.flat());
   const candidates=[];
   for(const d of docs){
    comparisons++;let supported=0;
    for(const variants of mapping){let match=false;for(const term of variants){probes++;if(d.words.has(term))match=true;}if(match)supported++;}
    if(supported){let overlap=0;for(const w of expanded)if(d.words.has(w))overlap++;
      candidates.push({id:d.id,supported,coverage:round(supported/words.length),score:round(overlap/(expanded.size+d.words.size-overlap))});}
   }
   candidates.sort((a,b)=>b.score-a.score||a.id-b.id);
   const top=candidates[0], margin=top?round(top.score-(candidates[1]?.score||0)):0;
   let reason=null;
   if(mode==="abstain")reason="ALWAYS_ABSTAIN";
   else if(!top)reason="NO_MATCH";
   else if(gate&&ambiguous)reason="AMBIGUOUS_RELATION";
   else if(gate&&(top.coverage<gate.coverage||top.supported<gate.minSupported))reason="INSUFFICIENT_SUPPORT";
   else if(gate&&(margin===0||margin<gate.margin))reason="INSUFFICIENT_MARGIN";
   const selected=reason?null:top.id;
   rows.push({id:q.id,family:q.family,target:q.target,selected,reason,margin,top:candidates.slice(0,3)});
  }
  const metrics={queries:rows.length,answerable:0,unanswerable:0,correct:0,wrong:0,false_accept:0,abstain_positive:0,abstain_negative:0,by_family:{}};
  for(const r of rows){const g=metrics.by_family[r.family]??={count:0,correct:0,wrong:0,false_accept:0,abstain:0};g.count++;
   if(r.target===null){metrics.unanswerable++;if(r.selected===null){metrics.abstain_negative++;g.abstain++;}else{metrics.false_accept++;g.false_accept++;}}
   else {metrics.answerable++;if(r.selected===null){metrics.abstain_positive++;g.abstain++;}else if(r.selected===r.target){metrics.correct++;g.correct++;}else{metrics.wrong++;g.wrong++;}}
  }
  metrics.admitted=metrics.correct+metrics.wrong+metrics.false_accept;metrics.coverage=round(metrics.admitted/rows.length);
  metrics.selective_error=metrics.admitted?round((metrics.wrong+metrics.false_accept)/metrics.admitted):null;
  return {metrics,cost:{candidate_comparisons:comparisons,support_probes:probes,relation_lookups:lookups},rows};
 }
 function calibrate(mode){
  const candidates=grid.map(gate=>({gate,metrics:run(fixture.calibration,mode,gate).metrics}));
  candidates.sort((a,b)=>(a.metrics.wrong+a.metrics.false_accept)-(b.metrics.wrong+b.metrics.false_accept)||b.metrics.correct-a.metrics.correct||b.gate.coverage-a.gate.coverage||b.gate.minSupported-a.gate.minSupported||b.gate.margin-a.gate.margin);
  return {selected:candidates[0].gate,grid:candidates};
 }
 const direct=calibrate("direct"), relational=calibrate("relational");
 return {schema:"memoria-abstention-result/v1",synthetic:true,authority:"NONE",calibration:{direct,relational},evaluation:{direct:run(fixture.evaluation,"direct",null),relational:run(fixture.evaluation,"relational",null),guarded_direct:run(fixture.evaluation,"direct",direct.selected),guarded_relational:run(fixture.evaluation,"relational",relational.selected),always_abstain:run(fixture.evaluation,"abstain",null)}};
}
