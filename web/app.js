'use strict';
const $ = id => document.getElementById(id);
const icons = {'Personnage':'♞','Aventure':'⚔','Quêtes':'✧','Métiers':'⚒','Atelier':'⚙','Marché':'◈','Écurie':'♘','Donjons':'♜','Soins':'♥','Autres':'✦'};
const labels = {commencer:'Commencer',profil:'Mon personnage',inventaire:'Inventaire',niveau_max:'Progression',succes:'Mes succès',classement:'Classement',aide:'Guide du royaume',hunt:'Chasse sauvage',aventure:'Explorer',chasse:'Chasse classique',quete:'Quête de combat',boss:'Affronter un boss',regions:'Carte des régions',bestiary:'Bestiaire',chasser_region:'Chasse régionale',statistiques_chasse:'Trophées de chasse',quetes:'Quêtes permanentes',reclamer_quete:'Réclamer une quête',quotidien:'Récompense du jour',metiers:'Mes métiers',exercer:'Exercer un métier',recolter:'Récolte avancée',mine:'Miner',couper:'Couper du bois',peche:'Pêcher',travail:'Travailler',crafts:'Livre de recettes',fabriquer:'Fabriquer',equipements:'Paliers d’équipement',equiper:'Amélioration permanente',porter:'Porter un équipement',boutique:'Catalogue du marché',acheter:'Acheter',vendre:'Vendre',chevaux:'Visiter l’écurie',acheter_cheval:'Acheter un cheval',entrainer_cheval:'Entraîner mon cheval',donjons:'Les donjons',entrer_donjon:'Entrer dans un donjon',avancer_donjon:'Salle suivante',quitter_donjon:'Quitter le donjon',utiliser:'Boire une potion',repos:'Se reposer'};
const titles = {'Aventure':["L'appel de l'aventure","Explore. Combats. Écris ta légende."],'Personnage':['Ta légende prend forme','Retrouve ton héros, sa progression et ses exploits.'],'Quêtes':['Une histoire à accomplir','Relève les défis et récupère tes récompenses.'],'Métiers':['Le savoir des artisans','Récolte les richesses du royaume et perfectionne ton métier.'],'Atelier':['À la forge des légendes','Fabrique ton équipement et prépare les prochains combats.'],'Marché':['Les étals du royaume','Achète tes provisions et échange tes trésors.'],'Écurie':['Un compagnon de route','Trouve ta monture et entraîne-la pour les batailles.'],'Donjons':['Dans les profondeurs','Franchis les salles. Affronte leurs gardiens.'],'Soins':['Une halte bien méritée','Reprends des forces avant de repartir.']};
let bootstrap, state, category='Aventure', activeCommand, busy=false, toastTimer;
function node(tag, cls, text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500)}
async function api(path,data){
 const options=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Game-Session':bootstrap.csrf},body:JSON.stringify(data)};
 const response=await fetch('/api/'+path,options);
 if(!response.ok){let detail;try{detail=(await response.json()).error}catch{}throw new Error(detail|| (response.status===401?'Choisis à nouveau ton personnage.':'Le jeu ne répond pas. Vérifie que sa fenêtre est ouverte.'))}
 return response.json();
}
function log(command,messages){
 const entry=node('article','journal-entry');
 entry.append(node('span','journal-time',new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})+' · '+(labels[command]||command).toUpperCase()));
 for(const message of messages){entry.append(node('p','',message.replace(/\*\*/g,'').replace(/\x60/g,'')))}
 $('journal').prepend(entry);
 while($('journal').children.length>30)$('journal').lastElementChild.remove();
 $('journal').scrollTop=0;
}
function itemIcon(key){if(key.includes('potion')||key==='elixir')return '⚗';if(key.includes('armure'))return '⛨';if(key.includes('epee')||key.includes('lame'))return '⚔';if(key.includes('bois')||key==='chene'||key==='if')return '♣';if(key.includes('poisson')||key==='truite'||key==='saumon')return '♓';if(key.includes('relique')||key.includes('cristal'))return '✧';return '◈'}
function paint(){
 const p=state.player;
 $('hero-name').textContent='Héros du royaume';$('hero-name').title='Discord : '+p.id;
 $('level').textContent='NIVEAU '+p.level;
 $('hp-text').textContent=p.hp+' / '+p.max_hp;
 $('hp-bar').style.width=Math.max(0,Math.min(100,p.hp/p.max_hp*100))+'%';
 $('xp-text').textContent=p.level>=100?'Niveau maximum':p.xp+' / '+p.level*75;
 $('xp-bar').style.width=(p.level>=100?100:Math.min(100,p.xp/(p.level*75)*100))+'%';
 $('attack').textContent=p.atk;$('defense').textContent=p.defense;$('gold').textContent=p.gold.toLocaleString('fr-FR');
 const regions=["Les Prairies d'Aube",'Les Bois de Brume','Le Désert de Verre','Le Marais des Murmures','Les Pics de Givre','Les Cavernes de Braise','Les Ruines Astrales','La Cité Engloutie','Le Royaume du Néant','Le Trône Éternel'];
 const tier=Math.min(9,Math.floor(p.level/10));
 $('world-name').textContent=p.dungeon?'Donjon : salle '+(p.dungeon_floor+1):regions[tier];
 $('region-tier').textContent=p.dungeon?'EXPÉDITION EN COURS':'RÉGION '+(tier+1)+' / 10';
 $('bag').replaceChildren();
 for(const item of state.inventory.slice(0,8)){
  const slot=node('div','bag-slot',itemIcon(item.item));slot.title=(bootstrap.items[item.item]?.[0]||item.item)+' × '+item.qty;
  slot.append(node('small','',item.qty));$('bag').append(slot);
 }
 if(!state.inventory.length)$('bag').append(node('p','muted','Ta besace est vide.'));
 $('bag-count').textContent=state.inventory.length+' objets';
 $('connection').replaceChildren(node('i','live-dot'),document.createTextNode('Sauvegarde synchronisée'));
 paintActions();
}
function navigate(next){
 category=next;
 for(const button of $('navigation').children)button.classList.toggle('active',button.dataset.category===next);
 $('crumb').textContent=next;$('page-title').textContent=(titles[next]||[next])[0];$('page-subtitle').textContent=(titles[next]||['','Toutes les actions du royaume.'])[1];
 $('world').hidden=next!=='Aventure';$('actions-title').textContent=next==='Aventure'?'Choisis ta prochaine action':next+' — les actions';
 $('search').value='';paintActions();
}
function remaining(name){
 const alias={hunt:'chasse',recolter:'',chasser_region:'region_hunt'};
 return Math.max(0,Math.ceil((state?.cooldowns[alias[name]??name]||0)-Date.now()/1000));
}
function paintActions(){
 if(!bootstrap)return;
 const query=$('search').value.trim().toLocaleLowerCase('fr');
 const commands=bootstrap.commands.filter(c=>(query||c.category===category)&&((labels[c.name]||c.name)+' '+c.name+' '+c.description).toLocaleLowerCase('fr').includes(query));
 $('actions').replaceChildren();$('command-count').textContent=commands.length+' actions';$('empty-search').hidden=commands.length!==0;
 for(const c of commands){
  const button=node('button','action-card');button.type='button';
  button.append(node('span','action-icon',icons[c.category]||'✦'));
  const copy=node('div');copy.append(node('h3','',labels[c.name]||c.name),node('p','',c.description));
  const wait=remaining(c.name);if(wait)copy.append(node('p','cooldown','⏳ '+wait+' s'));
  button.append(copy,node('span','arrow','↗'));button.disabled=busy;button.addEventListener('click',()=>openCommand(c));
  $('actions').append(button);
 }
}
function openCommand(command){
 if(busy)return;
 if(!command.parameters.length){execute(command,{});return}
 activeCommand=command;$('dialog-category').textContent=command.category;$('dialog-title').textContent=labels[command.name]||command.name;$('dialog-description').textContent=command.description;
 $('fields').replaceChildren();$('form-error').textContent='';
 for(const p of command.parameters){
  const label=node('label','',p.name==='objet'?'Objet':p.name==='quantite'?'Quantité':p.name==='numero'?'Numéro du donjon':p.name==='region'?'Région (1 à 10)':p.name==='metier'?'Métier':'Nom');label.htmlFor='field-'+p.name;
  let input;
  if(p.options.length){input=node('select');for(const option of p.options){const o=node('option','',option.label);o.value=option.value;input.append(o)}}
  else{input=node('input');input.type=p.type==='integer'?'number':'text';if(p.min!==null)input.min=p.min;if(p.max!==null)input.max=p.max;if(input.type==='number')input.step='1'}
  input.id='field-'+p.name;input.name=p.name;input.required=p.required;
  if(p.default!==null)input.value=p.default;
  if(p.type==='integer'&&p.required)input.value=p.min??1;
  $('fields').append(label,input);
 }
 $('action-dialog').showModal();
}
async function execute(command,args){
 if(busy)return;busy=true;paintActions();$('confirm-action').disabled=true;
 try{
  const result=await api('action',{command:command.name,args});state=result.state;paint();
  log(command.name,result.messages);$('action-dialog').close();toast((labels[command.name]||command.name)+' : résultat dans le journal');
 }catch(error){if($('action-dialog').open)$('form-error').textContent=error.message;else toast(error.message)}
 finally{busy=false;$('confirm-action').disabled=false;paintActions()}
}
$('choose').addEventListener('submit',async event=>{
 event.preventDefault();const button=event.submitter;button.disabled=true;
 try{state=await api('select',{id:$('characters').value});$('login').hidden=true;paint();navigate(category)}
 catch(error){$('login-error').textContent=error.message}finally{button.disabled=false}
});
$('action-form').addEventListener('submit',event=>{event.preventDefault();execute(activeCommand,Object.fromEntries(new FormData(event.target)))});
$('close-dialog').addEventListener('click',()=>$('action-dialog').close());
$('switch-player').addEventListener('click',()=>{$('login').hidden=false});
$('search').addEventListener('input',paintActions);
for(const [id,name] of [['hunt','hunt'],['boss','boss'],['daily','quotidien'],['open-bag','inventaire']]){
 $(id).addEventListener('click',()=>{const c=bootstrap?.commands.find(c=>c.name===name);if(c)openCommand(c)});
}
$('refresh').addEventListener('click',async()=>{try{state=await api('state');paint();toast('Progression actualisée.')}catch(error){toast(error.message)}});
async function start(){
 try{
  bootstrap=await api('bootstrap');
  const categories=[...new Set(bootstrap.commands.map(c=>c.category))];
  for(const category of Object.keys(icons).filter(c=>categories.includes(c))){
   const button=node('button');button.dataset.category=category;button.append(node('span','',icons[category]),document.createTextNode(category),node('small','',bootstrap.commands.filter(c=>c.category===category).length));
   button.addEventListener('click',()=>navigate(category));$('navigation').append(button);
  }
  for(const p of bootstrap.players){const option=node('option','','Niveau '+p.level+' · '+p.gold+' or · Discord '+p.id);option.value=p.id;$('characters').append(option)}
  $('save-note').textContent='Sauvegarde : '+bootstrap.save+' · '+bootstrap.players.length+' personnage(s)';
  if(!bootstrap.players.length){$('login-error').textContent='Aucun personnage existant. Vérifie que le jeu se trouve dans le dossier de ta sauvegarde.';$('choose').querySelector('button').disabled=true}
  try{state=await api('state');$('login').hidden=true;paint();navigate(category)}catch{}
 }catch(error){$('login-error').textContent=error.message;$('save-note').textContent='Connexion au jeu indisponible.'}
}
setInterval(async()=>{
 if(!state||busy||!$('login').hidden||document.hidden)return;
 try{state=await api('state');paint()}catch{$('connection').textContent='Connexion interrompue — ouvre la fenêtre du jeu';}
},5000);
start();
