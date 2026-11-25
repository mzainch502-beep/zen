// Simulation-only, single-owner authentication. No exchange credentials.
const enc=new TextEncoder();
const hex=b=>Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,"0")).join("");
const random=()=>hex(crypto.getRandomValues(new Uint8Array(32)));
const digest=async s=>hex(await crypto.subtle.digest("SHA-256",enc.encode(s)));
async function passwordHash(password,salt){const key=await crypto.subtle.importKey("raw",enc.encode(password),"PBKDF2",false,["deriveBits"]);return hex(await crypto.subtle.deriveBits({name:"PBKDF2",hash:"SHA-256",salt:enc.encode(salt),iterations:100000},key,256))}
function equal(a,b){if(typeof a!=="string"||typeof b!=="string"||a.length!==b.length)return false;let d=0;for(let i=0;i<a.length;i++)d|=a.charCodeAt(i)^b.charCodeAt(i);return d===0}
const reply=(detail,status)=>Response.json({detail},{status,headers:{"Cache-Control":"no-store"}});
export async function authenticate(req,env){const token=req.headers.get("Authorization")?.match(/^Bearer ([a-f0-9]{64})$/)?.[1];if(!token)return false;return !!await env.DB.prepare("SELECT 1 FROM owner_sessions WHERE token_hash=? AND expires_at>?").bind(await digest(token),Date.now()).first()}
export async function auth(req,env,path){if(req.method!=="POST")return reply("Method not allowed",405);
if(path==="/auth/logout"){const token=req.headers.get("Authorization")?.slice(7);if(token)await env.DB.prepare("DELETE FROM owner_sessions WHERE token_hash=?").bind(await digest(token)).run();return Response.json({ok:true})}
if(!["/auth/setup","/auth/login"].includes(path))return reply("Not found",404);
const now=Date.now(),bucket=Math.floor(now/900000),ip=await digest(req.headers.get("CF-Connecting-IP")||"unknown");
const limit=await env.DB.prepare("INSERT INTO auth_limits(ip,bucket,n) VALUES(?,?,1) ON CONFLICT(ip,bucket) DO UPDATE SET n=n+1 RETURNING n").bind(ip,bucket).first();if(limit.n>10)return reply("Try again later",429);
let b;try{b=await req.json()}catch{return reply("Invalid JSON",400)}
const email=typeof b.email==="string"?b.email.trim().toLowerCase():"",password=b.password;
if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||email.length>254||typeof password!=="string"||password.length<12||password.length>128)return reply("Invalid credentials",400);
if(path==="/auth/setup"){if(!env.OWNER_SETUP_TOKEN||!equal(b.setup_token,env.OWNER_SETUP_TOKEN))return reply("Setup unavailable",403);const salt=random(),hash=await passwordHash(password,salt);const result=await env.DB.prepare("INSERT OR IGNORE INTO owner_account(id,email,salt,password_hash) VALUES(1,?,?,?)").bind(email,salt,hash).run();return result.meta.changes===1?Response.json({ok:true},{status:201}):reply("Owner already exists",409)}
const owner=await env.DB.prepare("SELECT * FROM owner_account WHERE id=1").first();const hash=await passwordHash(password,owner?.salt||"invalid-owner");if(!owner||!equal(hash,owner.password_hash)||email!==owner.email)return reply("Invalid credentials",401);
const token=random();await env.DB.batch([env.DB.prepare("DELETE FROM owner_sessions WHERE expires_at<=?").bind(now),env.DB.prepare("DELETE FROM auth_limits WHERE bucket<?").bind(bucket-1),env.DB.prepare("INSERT INTO owner_sessions(token_hash,expires_at) VALUES(?,?)").bind(await digest(token),now+86400000)]);return Response.json({token},{headers:{"Cache-Control":"no-store"}})}
