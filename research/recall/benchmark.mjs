// Deterministic synthetic retrieval comparison; no production data or runtime integration.
export function evaluate(f){
 const methods=["coverage","jaccard","tfidf","relational_jaccard","shuffled_relational"];
 const toks=s=>new Set(s.toLowerCase().match(/[a-z0-9]+/g)||[]);
 const round=n=>Number(n.toFixed(12));
 const documents=f.documents.map(d=>({...d,words:toks(d.text)}));
 const df=new Map();for(const d of documents)for(const w of d.words)df.set(w,(df.get(w)||0)+1);
 const idf=w=>1+Math.log((1+documents.length)/(1+(df.get(w)||0)));
 const keys=Object.keys(f.relations).sort(), values=keys.map(k=>f.relations[k]);
 const shuffled=Object.fromEntries(keys.map((k,i)=>[k,values[(i+2)%values.length]]));
 const summary={},rows=[];
 for(const method of methods){
  const metrics={positives:0,hit1:0,hit3:0,mrr3:0,negatives:0,false_accepts:0,abstentions:0,by_family:{},cost:{document_tokens_prepared:documents.reduce((n,d)=>n+d.words.size,0),document_frequency_updates:method==="tfidf"?documents.reduce((n,d)=>n+d.words.size,0):0,query_term_lookups:0,relation_lookups:0,added_query_terms:0,candidate_comparisons:0,intersection_probes:0,weighted_term_visits:0,document_bytes:f.documents.reduce((n,d)=>n+d.text.length,0),relation_map_bytes:method.includes("relational")?JSON.stringify(method==="shuffled_relational"?shuffled:f.relations).length:0}};
  for(const q of f.queries){
   const words=toks(q.text), original=words.size;metrics.cost.query_term_lookups+=original;
   if(method.includes("relational")){const map=method==="shuffled_relational"?shuffled:f.relations;for(const w of [...words]){metrics.cost.relation_lookups++;if(Object.hasOwn(map,w))words.add(map[w]);}metrics.cost.added_query_terms+=words.size-original;}
   let qnorm=0;if(method==="tfidf"){for(const w of words){qnorm+=idf(w)**2;metrics.cost.weighted_term_visits++;}}
   const ranked=[];
   for(const d of documents){
    metrics.cost.candidate_comparisons++;
    let overlap=0, dot=0;for(const w of words){metrics.cost.intersection_probes++;if(d.words.has(w)){overlap++;if(method==="tfidf"){dot+=idf(w)**2;metrics.cost.weighted_term_visits++;}}}
    if(!overlap)continue;
    let score;
    if(method==="coverage")score=overlap/words.size;
    else if(method==="tfidf"){let norm=0;for(const w of d.words){norm+=idf(w)**2;metrics.cost.weighted_term_visits++;}score=dot/Math.sqrt(qnorm*norm);}
    else score=overlap/(words.size+d.words.size-overlap);
    ranked.push({id:d.id,score:round(score)});
   }
   ranked.sort((a,b)=>b.score-a.score||a.id-b.id);
   const top=ranked.slice(0,3), rank=q.target===null?0:top.findIndex(x=>x.id===q.target)+1;
   const g=metrics.by_family[q.family]??={count:0,hit1:0,hit3:0,abstentions:0,false_accepts:0};g.count++;
   if(!top.length){metrics.abstentions++;g.abstentions++;}
   if(q.target===null){metrics.negatives++;if(top.length){metrics.false_accepts++;g.false_accepts++;}}
   else{metrics.positives++;if(rank===1){metrics.hit1++;g.hit1++;}if(rank){metrics.hit3++;g.hit3++;metrics.mrr3+=1/rank;}}
   rows.push({method,query_id:q.id,family:q.family,target:q.target,top,rank,abstained:!top.length});
  }
  metrics.mrr3=round(metrics.mrr3/metrics.positives);
  summary[method]=metrics;
 }
 return {schema:"memoria-recall-benchmark-result/v1",synthetic:true,authority:"NONE",summary,rows};
}
