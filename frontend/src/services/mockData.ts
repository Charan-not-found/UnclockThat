import type { Inspection, ModelInfo, Pipeline } from '../types'
export const industries: Record<string, string[]> = { Automotive: ['Brake disc','Gear housing'], Electronics: ['PCB','Connector'], Textile: ['Woven fabric'] }
export const pipelines: Pipeline[] = [
 { id:'p1', name:'Surface defect (detect → classify)', industry:'Any' },
 { id:'p2', name:'Fast screen (anomaly only)', industry:'Any' },
 { id:'p3', name:'Conditional deep scan', industry:'Any' } ]
const st = ['pass','pass','fail','review','pass','fail'] as const
export const inspections: Inspection[] = Array.from({ length: 24 }, (_, i) => {
 const status = st[i % 6]; const ind = Object.keys(industries)[i % 3]
 return { id:`INS-${1042 - i}`, date:new Date(Date.now() - i*5.4e6).toISOString(), industry:ind, product:industries[ind][i%industries[ind].length], pipeline:pipelines[i%3].name, status,
  score: status==='pass'? 88 - (i%7) : status==='review'? 71 : 42 + (i%9), severity: status==='pass'?'none': status==='review'?'low': i%2?'high':'medium', defects: status==='pass'?0: 1 + (i%3) } })
export const models: ModelInfo[] = [
 { id:'m1', name:'PatchCore-v2', task:'Anomaly detection', version:'2.1.0', enabled:true, accuracy:96.4 },
 { id:'m2', name:'DefectNet', task:'Defect classification', version:'1.4.2', enabled:true, accuracy:92.1 },
 { id:'m3', name:'SegLocalizer', task:'Localization', version:'0.9.0', enabled:false, accuracy:88.7 } ]
export const trend = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d,i)=>({ day:d, inspections:[42,55,48,63,58,31,27][i], anomalies:[5,9,6,11,8,4,3][i] }))
export const distribution = [{ name:'Scratch', value:34 },{ name:'Crack', value:18 },{ name:'Contamination', value:22 },{ name:'Misalignment', value:11 }]
