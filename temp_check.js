
(function(){'use strict';

var ageEl=document.getElementById('rpAge'),
  retireAgeEl=document.getElementById('rpRetireAge'),
  lifeExpEl=document.getElementById('rpLifeExp'),
  savingsEl=document.getElementById('rpSavings'),
  monthlyEl=document.getElementById('rpMonthly'),
  returnEl=document.getElementById('rpAnnualReturn'),
  stdDevEl=document.getElementById('rpStdDev'),
  taxPctEl=document.getElementById('rpTaxPct'),
  retireTaxRateEl=document.getElementById('rpRetireTaxRate'),
  taxBarTrad=document.getElementById('rpTaxBarTraditional'),
  taxBarRoth=document.getElementById('rpTaxBarRoth'),
  inflationEl=document.getElementById('rpInflation'),
  escalationEl=document.getElementById('rpEscalation'),
  ssToggle=document.getElementById('rpSsToggle'),
  ssAmountEl=document.getElementById('rpSsAmount'),
  ssAgeEl=document.getElementById('rpSsAge'),
  pensionEl=document.getElementById('rpPension'),
  rentalEl=document.getElementById('rpRental'),
  partTimeEl=document.getElementById('rpPartTime'),
  withdrawStrategyEl=document.getElementById('rpWithdrawStrategy'),
  goalIncomeEl=document.getElementById('rpGoalIncome'),
  calcBtn=document.getElementById('rpCalcBtn'),
  mcBtn=document.getElementById('rpMcBtn'),
  copyBtn=document.getElementById('rpCopyBtn'),
  dlBtn=document.getElementById('rpDlBtn'),
  emptyState=document.getElementById('rpEmpty'),
  resultsDiv=document.getElementById('rpResults'),
  nestEggEl=document.getElementById('rpNestEgg'),
  totalContribEl=document.getElementById('rpTotalContrib'),
  totalGrowthEl=document.getElementById('rpTotalGrowth'),
  goalStatusEl=document.getElementById('rpGoalStatus'),
  monthlyIncomeEl=document.getElementById('rpMonthlyIncome'),
  runwayEl=document.getElementById('rpRunway'),
  goalProgressEl=document.getElementById('rpGoalProgress'),
  insightsEl=document.getElementById('rpInsights'),
  projBody=document.getElementById('rpProjBody'),
  drawBody=document.getElementById('rpDrawBody'),
  compareGrid=document.getElementById('rpCompareGrid'),
  s2Monthly=document.getElementById('rpS2Monthly'),
  s2Return=document.getElementById('rpS2Return'),
  s2RetireAge=document.getElementById('rpS2RetireAge'),
  toastEl=document.getElementById('rpToast'),
  hiToggle=document.getElementById('rpHiToggle'),
  hiCount=document.getElementById('rpHiCount'),
  hiClear=document.getElementById('rpHiClear'),
  hiWrap=document.getElementById('rpHiWrap'),
  hiList=document.getElementById('rpHiList'),
  rpChart=document.getElementById('rpChart'),
  mcProbEl=document.getElementById('rpMcProb'),
  mcP10=document.getElementById('rpMcP10'),
  mcP25=document.getElementById('rpMcP25'),
  mcP50=document.getElementById('rpMcP50'),
  mcP75=document.getElementById('rpMcP75'),
  mcP90=document.getElementById('rpMcP90'),
  mcChart=document.getElementById('rpMcChart'),
  ccyEl=document.getElementById('rpCurrency'),
  addExpBtn=document.getElementById('rpAddExpense'),
  gsBtn=document.getElementById('rpGoalSeekBtn'),
  gsResult=document.getElementById('rpGoalSeekResult'),
  csvProjBtn=document.getElementById('rpCsvProjBtn'),
  csvDrawBtn=document.getElementById('rpCsvDrawBtn');

var tt,history=[],STORE_KEY='sb_rp',HIST_KEY='sb_rp_h';
try{var h=JSON.parse(localStorage.getItem(HIST_KEY)||'[]');if(Array.isArray(h))history=h}catch(e){}

var lastDrawData1=null,lastDrawData2=null,lastNestEgg1=0,lastNestEgg2=0;
var lastProjData1=null,lastProjData2=null;
var lastRetireAge=65,lastLifeExp=95,lastCurAge=30;

var CURRENCY_RATES={USD:1,EUR:0.92,GBP:0.79,JPY:149,INR:83,CAD:1.37,AUD:1.53,CHF:0.88,CNY:7.24,BRL:5.05};
var CURRENCY_LOCALES={USD:'en-US',EUR:'de-DE',GBP:'en-GB',JPY:'ja-JP',INR:'en-IN',CAD:'en-CA',AUD:'en-AU',CHF:'de-CH',CNY:'zh-CN',BRL:'pt-BR'};
var CURRENCY_SYMBOLS={USD:'$',EUR:'\u20AC',GBP:'\u00A3',JPY:'\u00A5',INR:'\u20B9',CAD:'C$',AUD:'A$',CHF:'Fr',CNY:'\u00A5',BRL:'R$'};
var currentCurrency='USD';
try{var saved=localStorage.getItem('sb_rp_ccy');if(saved&&CURRENCY_RATES[saved])currentCurrency=saved;ccyEl.value=currentCurrency}catch(e){}

var maxExpIdx=2;
function addExpenseRow(){
  maxExpIdx++;
  var div=document.getElementById('rpExpenses');
  var row=document.createElement('div');row.className='rp-exp-row';
  row.innerHTML='<input type="text" class="rp-input-sm" placeholder="Age" id="rpExpAge'+maxExpIdx+'" inputmode="numeric"><input type="text" class="rp-input-sm" placeholder="Amount" id="rpExpAmt'+maxExpIdx+'" inputmode="numeric"><button type="button" class="rp-del" data-idx="'+maxExpIdx+'" aria-label="Remove expense">\u2715</button>';
  div.appendChild(row);
  attachExpDel(row.querySelector('.rp-del'));
}
function attachExpDel(btn){btn.addEventListener('click',function(){var row=this.closest('.rp-exp-row');if(row&&document.getElementById('rpExpenses').children.length>1){row.remove()}})}
document.querySelectorAll('#rpExpenses .rp-del').forEach(attachExpDel);
addExpBtn.addEventListener('click',addExpenseRow);

function getExpenses(){
  var exps=[];
  var rows=document.querySelectorAll('#rpExpenses .rp-exp-row');
  rows.forEach(function(row){
    var ageI=row.querySelector('[id^=rpExpAge]');var amtI=row.querySelector('[id^=rpExpAmt]');
    if(ageI&&amtI){var a=parseFloat(ageI.value)||0;var v=parseFloat(amtI.value)||0;if(a>0&&v>0)exps.push({age:a,amt:v})}
  });
  return exps;
}

function fmtCurrency(n){
  if(isNaN(n)||!isFinite(n))n=0;
  var rate=CURRENCY_RATES[currentCurrency]||1;
  var locale=CURRENCY_LOCALES[currentCurrency]||'en-US';
  var code=currentCurrency;
  try{return new Intl.NumberFormat(locale,{style:'currency',currency:code,minimumFractionDigits:0,maximumFractionDigits:0}).format(n*rate)}catch(e){
    var sym=CURRENCY_SYMBOLS[currentCurrency]||'$';
    var converted=n*rate;
    return sym+Math.round(converted).toLocaleString(locale);
  }
}

function fmtPct(n){return (n*100).toFixed(2)+'%'}

function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}

function toast(m){toastEl.textContent=m;toastEl.classList.add('show');clearTimeout(tt);tt=setTimeout(function(){toastEl.classList.remove('show')},2200)}

function gaussRandom(){
  var u=0,v=0;
  while(u===0)u=Math.random();
  while(v===0)v=Math.random();
  return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);
}

function updateTaxBar(){
  var pct=parseFloat(taxPctEl.value)||70;
  if(pct<0)pct=0;if(pct>100)pct=100;
  taxBarTrad.style.width=pct+'%';
  taxBarRoth.style.width=(100-pct)+'%';
}
taxPctEl.addEventListener('input',updateTaxBar);

function runCalc(withMc){
  var curAge=parseFloat(ageEl.value)||0,
    retireAge=parseFloat(retireAgeEl.value)||65,
    lifeExp=parseFloat(lifeExpEl.value)||95,
    savings=parseFloat(savingsEl.value)||0,
    monthly=parseFloat(monthlyEl.value)||0,
    annReturn=parseFloat(returnEl.value)||7,
    stdDev=parseFloat(stdDevEl.value)||15,
    infl=parseFloat(inflationEl.value)||3,
    escPct=parseFloat(escalationEl.value)||0,
    includeSs=ssToggle.checked,
    ssAmt=parseFloat(ssAmountEl.value)||0,
    ssAge=parseFloat(ssAgeEl.value)||67,
    pension=parseFloat(pensionEl.value)||0,
    rental=parseFloat(rentalEl.value)||0,
    partTime=parseFloat(partTimeEl.value)||0,
    goalIncome=parseFloat(goalIncomeEl.value)||0,
    wdStrategy=withdrawStrategyEl.value,
    taxPct=parseFloat(taxPctEl.value)||70,
    retireTaxRate=parseFloat(retireTaxRateEl.value)||15;
  var expenses=getExpenses();

  if(curAge<=0||retireAge<=curAge){toast('Retirement age must be after your current age');return}

  var r=annReturn/100,iRate=infl/100,escRate=escPct/100,taxDec=retireTaxRate/100,tradPct=taxPct/100,rothPct=1-tradPct;
  var yearsToRetire=retireAge-curAge;
  var balance=savings,balance2=savings;
  var tradBal=savings*tradPct,rothBal=savings*rothPct;
  var totalContribs=0,totalContribs2=0;
  var yearlyData1=[],yearlyData2=[];

  var s2monthly=parseFloat(s2Monthly.value)||monthly,
    s2ret=parseFloat(s2Return.value)||annReturn,
    s2ra=parseFloat(s2RetireAge.value)||retireAge;
  var r2=s2ret/100;
  var yearsToRetire2=s2ra-curAge;

  for(var y=1;y<=Math.max(yearsToRetire,yearsToRetire2);y++){
    var yrAge=curAge+y;
    var add=monthly;
    if(escRate>0&&y>1)add=monthly*Math.pow(1+escRate,y-1);
    var add2=s2monthly;
    if(escRate>0&&y>1)add2=s2monthly*Math.pow(1+escRate,y-1);

    if(y<=yearsToRetire){
      var start1=balance;
      var yrContrib1=add*12;
      var yrTradContrib=yrContrib1*tradPct;
      var yrRothContrib=yrContrib1*rothPct;
      balance+=yrContrib1;
      tradBal+=yrTradContrib;rothBal+=yrRothContrib;
      var yrGrowth1=balance*r;
      tradBal+=yrGrowth1*tradPct;rothBal+=yrGrowth1*rothPct;
      balance+=yrGrowth1;
      totalContribs+=yrContrib1;
      yearlyData1.push({age:yrAge,year:y,start:start1,contrib:yrContrib1,growth:yrGrowth1,end:balance,trad:tradBal,roth:rothBal});
    }

    if(y<=yearsToRetire2){
      var start2=balance2;
      var yrContrib2=add2*12;
      balance2+=yrContrib2;
      var yrGrowth2=balance2*r2;
      balance2+=yrGrowth2;
      totalContribs2+=yrContrib2;
      yearlyData2.push({age:yrAge,year:y,start:start2,contrib:yrContrib2,growth:yrGrowth2,end:balance2});
    }
  }

  var nestEgg1=balance,nestEgg2=balance2;
  var totalGrowth1=nestEgg1-savings-totalContribs;
  if(totalGrowth1<0)totalGrowth1=0;
  var tradNestEgg=tradBal,rothNestEgg=rothBal;

  var addIncomeMonthly=pension+rental+partTime;

  var drawData1=projectDrawdown(nestEgg1,annReturn,goalIncome,infl,includeSs,ssAmt,ssAge,retireAge,lifeExp,wdStrategy,addIncomeMonthly,expenses,tradNestEgg,retireTaxRate);
  var drawData2=projectDrawdown(nestEgg2,s2ret,goalIncome,infl,includeSs,ssAmt,ssAge,s2ra,lifeExp,wdStrategy,addIncomeMonthly,expenses,nestEgg2*0.7,retireTaxRate);

  lastDrawData1=drawData1;
  lastDrawData2=drawData2;
  lastNestEgg1=nestEgg1;
  lastNestEgg2=nestEgg2;
  lastProjData1=yearlyData1;
  lastProjData2=yearlyData2;
  lastRetireAge=retireAge;
  lastLifeExp=lifeExp;
  lastCurAge=curAge;

  var monthsLast1=drawData1.months,duration1=drawData1.years;
  var yearsLast=Math.min(duration1,lifeExp-retireAge);

  var totalMonthlyIncome=0;
  if(drawData1.avgMonthly>0)totalMonthlyIncome=drawData1.avgMonthly;

  emptyState.hidden=true;resultsDiv.hidden=false;

  nestEggEl.textContent=fmtCurrency(nestEgg1);
  totalContribEl.textContent=fmtCurrency(totalContribs);
  totalGrowthEl.textContent=fmtCurrency(totalGrowth1);

  if(goalIncome>0){
    var monthlyAvail=drawData1.avgMonthly||0;
    monthlyIncomeEl.textContent=fmtCurrency(monthlyAvail);
    var meetsGoal=monthlyAvail>=goalIncome;
    var fullDuration=yearsLast>=(lifeExp-retireAge);
    goalStatusEl.className='rp-stat';
    if(meetsGoal&&fullDuration){goalStatusEl.classList.add('success');goalStatusEl.querySelector('.sv').textContent='On Track'}
    else if(meetsGoal){goalStatusEl.classList.add('warning');goalStatusEl.querySelector('.sv').textContent='Short Duration'}
    else{goalStatusEl.classList.add('danger');goalStatusEl.querySelector('.sv').textContent='Shortfall'}
  }else{
    monthlyIncomeEl.textContent=fmtCurrency(totalMonthlyIncome);
    goalStatusEl.className='rp-stat';
    goalStatusEl.querySelector('.sv').textContent='--';
  }

  runwayEl.textContent=yearsLast.toFixed(1)+' yrs';

  renderGoalProgress(totalMonthlyIncome,goalIncome,yearsLast,lifeExp,retireAge);
  var extraIncomeTotal=pension+rental+partTime;
  renderInsights(nestEgg1,totalContribs,totalMonthlyIncome,goalIncome,yearsLast,lifeExp,retireAge,curAge,extraIncomeTotal,wdStrategy,tradNestEgg,rothNestEgg,retireTaxRate);
  renderProjTable(yearlyData1,retireAge);
  renderDrawTable(drawData1,retireAge,addIncomeMonthly);
  renderCompare(nestEgg1,drawData1,nestEgg2,drawData2,curAge,retireAge,s2ra);
  drawProjectionChart(yearlyData1,drawData1,curAge,retireAge,nestEgg1);
  saveHistory(curAge,retireAge,lifeExp,savings,monthly,annReturn,infl,escPct,includeSs,ssAmt,ssAge,goalIncome,nestEgg1,totalMonthlyIncome,yearsLast);

  if(withMc)runMonteCarlo(nestEgg1,curAge,retireAge,lifeExp,monthly,annReturn,stdDev,escRate,goalIncome,infl,includeSs,ssAmt,ssAge,wdStrategy,addIncomeMonthly,savings,expenses,tradNestEgg,retireTaxRate);
}

function calcDrawdownYear(bal,tradBal,retireTaxDec,goalIncome,iRate,wdAge,wdStrategy,initialNestEgg,firstYearWD,yrSs,yrAdditional,expenses,currentAge){
  var yrWithdraw;
  if(wdStrategy==='fourpct'){
    if(wdAge===1){firstYearWD=initialNestEgg*0.04;yrWithdraw=firstYearWD}
    else{yrWithdraw=firstYearWD*Math.pow(1+iRate,wdAge-1)}
  }else if(wdStrategy==='variable'){
    var vp=wdAge<=10?0.04:wdAge<=20?0.045:wdAge<=30?0.05:0.055;
    yrWithdraw=Math.max(bal*vp,goalIncome*12*Math.pow(1+iRate,wdAge-1)*0.5);
  }else{
    yrWithdraw=goalIncome>0?goalIncome*12*Math.pow(1+iRate,wdAge-1):0;
  }

  var netWithdraw=Math.max(0,yrWithdraw-yrSs-yrAdditional);

  var tradPortion=0,taxOnWd=0;
  if(tradBal>0&&netWithdraw>0){
    var fromTrad=Math.min(netWithdraw*(tradBal/Math.max(bal,1)),tradBal);
    taxOnWd=fromTrad*retireTaxDec;
    tradPortion=fromTrad;
  }

  var yrExpenses=0;
  expenses.forEach(function(e){if(e.age===currentAge)yrExpenses+=e.amt});

  var totalDeductions=netWithdraw+taxOnWd+yrExpenses;
  if(totalDeductions>bal){totalDeductions=bal;netWithdraw=Math.max(0,bal-taxOnWd-yrExpenses);netWithdraw=Math.min(netWithdraw,yrWithdraw-yrSs-yrAdditional)}

  return {yrWithdraw:yrWithdraw,netWithdraw:netWithdraw,taxOnWd:taxOnWd,yrExpenses:yrExpenses,firstYearWD:firstYearWD,tradPortion:tradPortion};
}

function projectDrawdown(nestEgg,annReturnPct,goalIncome,inflPct,includeSs,ssAmt,ssAge,retireAge,lifeExp,wdStrategy,addIncomeMonthly,expenses,tradNestEgg,retireTaxRate){
  var r=annReturnPct/100,iRate=inflPct/100,retireTaxDec=retireTaxRate/100;
  var bal=nestEgg,totalMonths=0,tradBal=tradNestEgg||0;
  var monthlySs=includeSs?ssAmt:0;
  var drawData=[];
  var ssStartAge=includeSs?ssAge:999;
  var totalWithdrawn=0,totalGrowth=0;
  var initialNestEgg=nestEgg;
  var firstYearWD=0;

  for(var age=retireAge;age<=lifeExp;age++){
    var startBal=bal,startTrad=tradBal;
    var yrAdditional=(addIncomeMonthly||0)*12;
    var yrSs=age>=ssStartAge?monthlySs*12:0;
    var wdAge=age-retireAge+1;

    if(bal<=0){drawData.push({age:age,start:startBal,withdraw:0,tax:0,ss:yrSs,additional:yrAdditional,expenses:0,growth:0,end:0,tradEnd:tradBal,depleted:true});continue}

    var yrInfo=calcDrawdownYear(bal,tradBal,retireTaxDec,goalIncome,iRate,wdAge,wdStrategy,initialNestEgg,firstYearWD,yrSs,yrAdditional,expenses,age);
    firstYearWD=yrInfo.firstYearWD;

    var totalDeductions=yrInfo.netWithdraw+yrInfo.taxOnWd+yrInfo.yrExpenses;
    var tradReduction=Math.min(yrInfo.tradPortion+yrInfo.taxOnWd,tradBal);
    tradBal-=tradReduction;if(tradBal<0)tradBal=0;
    bal-=totalDeductions;

    totalWithdrawn+=yrInfo.netWithdraw;
    if(bal<0){bal=0;drawData.push({age:age,start:startBal,withdraw:yrInfo.netWithdraw,tax:yrInfo.taxOnWd,ss:yrSs,additional:yrAdditional,expenses:yrInfo.yrExpenses,growth:0,end:0,tradEnd:tradBal,depleted:true});totalMonths=(age-retireAge)*12;continue}

    var yrGrowth=bal*r;
    bal+=yrGrowth;
    tradBal+=yrGrowth*(tradBal/Math.max(bal-yrGrowth,1)||0);
    totalGrowth+=yrGrowth;
    if(bal<0)bal=0;
    drawData.push({age:age,start:startBal,withdraw:yrInfo.netWithdraw,tax:yrInfo.taxOnWd,ss:yrSs,additional:yrAdditional,expenses:yrInfo.yrExpenses,growth:yrGrowth,end:bal,tradEnd:tradBal,depleted:false});
    totalMonths=(age-retireAge+1)*12;

    if(monthlySs>0)monthlySs*=(1+iRate);
    if(addIncomeMonthly>0)addIncomeMonthly*=(1+iRate);

    if(bal<=0)break;
  }

  var yearsLast=Math.floor(totalMonths/12);
  var avgMonthly=totalMonths>0?totalWithdrawn/totalMonths:0;
  return {data:drawData,months:totalMonths,years:yearsLast,avgMonthly:avgMonthly};
}

function renderGoalProgress(monthlyIncome,goalIncome,yearsLast,lifeExp,retireAge){
  if(goalIncome<=0){goalProgressEl.innerHTML='<div class="rp-empty">No goal set</div>';return}
  var maxYears=lifeExp-retireAge;
  var incomePct=Math.min(100,(monthlyIncome/goalIncome)*100);
  var durationPct=Math.min(100,(yearsLast/maxYears)*100);
  var color='var(--color-error)';
  if(incomePct>=100&&durationPct>=100)color='var(--color-success)';
  else if(incomePct>=80||durationPct>=80)color='var(--color-warning)';
  var h='<div class="mb-2"><div style="display:flex;justify-content:space-between;font-size:10px;font-weight:800"><span>Income Goal ('+fmtCurrency(monthlyIncome)+' / '+fmtCurrency(goalIncome)+')</span><span>'+incomePct.toFixed(0)+'%</span></div><div class="rp-progress"><div class="rp-progress-fill" style="width:'+incomePct+'%;background:'+color+'"></div></div></div>';
  h+='<div><div style="display:flex;justify-content:space-between;font-size:10px;font-weight:800"><span>Duration ('+yearsLast.toFixed(1)+' yr / '+maxYears+' yr)</span><span>'+durationPct.toFixed(0)+'%</span></div><div class="rp-progress"><div class="rp-progress-fill" style="width:'+durationPct+'%;background:'+color+'"></div></div></div>';
  goalProgressEl.innerHTML=h;
}

function renderInsights(nestEgg,totalContribs,monthlyIncome,goalIncome,yearsLast,lifeExp,retireAge,curAge,extraIncome,wdStrategy,tradNest,rothNest,retireTaxRate){
  var h='',maxYears=lifeExp-retireAge;
  if(goalIncome>0){
    if(monthlyIncome>=goalIncome)h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-success);color:#fff">Goal</span> Your projected income meets your goal</div>';
    else{h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-error);color:#fff">Shortfall</span> Monthly income of '+fmtCurrency(monthlyIncome)+' is below your '+fmtCurrency(goalIncome)+' goal by '+fmtCurrency(goalIncome-monthlyIncome)+'/mo</div>'}
  }
  if(yearsLast<maxYears){h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-warning);color:#fff">Duration</span> Funds last '+yearsLast.toFixed(1)+' years vs '+maxYears+' year goal</div>'}
  else{h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-success);color:#fff">Duration</span> Funds last through age '+(curAge+yearsLast).toFixed(0)+'</div>'}
  var growthPct=nestEgg>0?((nestEgg-totalContribs)/nestEgg*100):0;
  h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-primary);color:#fff">Growth</span> Investment growth makes up '+growthPct.toFixed(0)+'% of your nest egg</div>';
  if(tradNest>0){var taxEst=tradNest*retireTaxRate/100;h+='<div class="rp-insight mb-1"><span class="badge" style="background:var(--color-warning);color:#ff8">Tax</span> Traditional: '+fmtCurrency(tradNest)+' &bull; Roth: '+fmtCurrency(rothNest)+' &bull; Est. tax on withdrawal '+fmtCurrency(taxEst)+'/yr</div>'}
  var stratLabel='Fixed Dollar';
  if(wdStrategy==='fourpct')stratLabel='4% Rule';
  else if(wdStrategy==='variable')stratLabel='Variable Percentage';
  if(extraIncome>0)h+='<div class="rp-insight"><span class="badge" style="background:var(--color-info);color:#fff">Income</span> Additional income of '+fmtCurrency(extraIncome)+'/mo &bull; '+stratLabel+'</div>';
  else h+='<div class="rp-insight"><span class="badge" style="background:var(--color-info);color:#fff">Strategy</span> '+stratLabel+'</div>';
  insightsEl.innerHTML=h;
}

function renderProjTable(data,retireAge){
  var h='';
  data.forEach(function(d){
    h+='<tr><td>'+d.age+'</td><td>'+d.year+'</td><td style="text-align:right">'+fmtCurrency(d.start)+'</td><td style="text-align:right">'+fmtCurrency(d.contrib)+'</td><td style="text-align:right;color:var(--color-success)">'+fmtCurrency(d.growth)+'</td><td style="text-align:right;font-weight:900">'+fmtCurrency(d.end)+'</td></tr>';
  });
  projBody.innerHTML=h||'<tr><td colspan="6" class="rp-empty">No data</td></tr>';
}

function renderDrawTable(drawData,retireAge,addIncomeMonthly){
  var h='';
  drawData.data.forEach(function(d){
    h+='<tr><td>'+d.age+'</td><td>'+(d.age-retireAge+1)+'</td><td style="text-align:right">'+fmtCurrency(d.start)+'</td><td style="text-align:right;color:var(--color-error)">'+fmtCurrency(d.withdraw)+'</td><td style="text-align:right;color:var(--color-warning)">'+fmtCurrency(d.tax)+'</td><td style="text-align:right;color:var(--color-success)">'+fmtCurrency(d.ss)+'</td><td style="text-align:right;color:var(--color-info)">'+fmtCurrency(d.additional)+'</td><td style="text-align:right">'+fmtCurrency(d.growth)+'</td><td style="text-align:right;font-weight:900">'+fmtCurrency(d.end)+'</td></tr>';
  });
  drawBody.innerHTML=h||'<tr><td colspan="9" class="rp-empty">No data</td></tr>';
}

function renderCompare(nestEgg1,draw1,nestEgg2,draw2,curAge,retireAge1,retireAge2){
  var h='';
  h+='<div class="rp-scenario-card best"><div class="scn-name">Current Plan</div><div class="scn-val">'+fmtCurrency(nestEgg1)+'</div><div class="scn-sub">Nest Egg at '+retireAge1+'</div><div class="scn-sub" style="color:'+(draw1.avgMonthly>0?'var(--color-success)':'var(--color-error)')+'">'+fmtCurrency(draw1.avgMonthly)+'/mo</div><div class="scn-sub">Lasts '+draw1.years.toFixed(1)+' yrs</div></div>';
  h+='<div class="rp-scenario-card'+(nestEgg2>nestEgg1?' best':'')+'"><div class="scn-name">Alternative</div><div class="scn-val">'+fmtCurrency(nestEgg2)+'</div><div class="scn-sub">Nest Egg at '+retireAge2+'</div><div class="scn-sub" style="color:'+(draw2.avgMonthly>0?'var(--color-success)':'var(--color-error)')+'">'+fmtCurrency(draw2.avgMonthly)+'/mo</div><div class="scn-sub">Lasts '+draw2.years.toFixed(1)+' yrs</div></div>';
  compareGrid.innerHTML=h;
}

function drawProjectionChart(projData,drawData,curAge,retireAge,nestEgg){
  var ctx=rpChart.getContext('2d');
  var W=rpChart.parentElement.clientWidth;
  var dpr=window.devicePixelRatio||1;
  var H=260;
  rpChart.width=W*dpr;
  rpChart.height=H*dpr;
  rpChart.style.width=W+'px';
  rpChart.style.height=H+'px';
  ctx.scale(dpr,dpr);

  var allBalances=[];
  projData.forEach(function(d){allBalances.push(d.end)});
  drawData.data.forEach(function(d){allBalances.push(d.start);allBalances.push(d.end)});
  var maxVal=Math.max.apply(null,allBalances)*1.1||1000;

  var p=30,pt=20,pb=30;
  var cw=W-p*2,ch=H-pt-pb;

  ctx.clearRect(0,0,W,H);

  var textColor='rgba(255,255,255,0.35)';
  var gridColor='rgba(255,255,255,0.08)';
  var lineColor='hsl(var(--p,221.2 83.2% 53.3%))';
  var lineColor2='hsl(var(--su,158.6 83.5% 44.1%))';
  try{
    var cs=getComputedStyle(document.documentElement);
    var pVal=cs.getPropertyValue('--p').trim();
    var suVal=cs.getPropertyValue('--su').trim();
    if(pVal)lineColor='hsl('+pVal+')';
    if(suVal)lineColor2='hsl('+suVal+')';
  }catch(e){}

  ctx.strokeStyle=gridColor;
  ctx.lineWidth=0.5;
  var numGL=5;
  for(var i=0;i<=numGL;i++){
    var y=pt+ch-(ch/numGL)*i;
    ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(p+cw,y);ctx.stroke();
    ctx.fillStyle=textColor;ctx.font='8px monospace';ctx.textAlign='right';
    ctx.fillText(fmtCurrency(maxVal/numGL*i),p-4,y+3);
  }

  function drawLine(data,color,getVal){
    if(!data||data.length<2)return;
    ctx.strokeStyle=color;
    ctx.lineWidth=2;
    ctx.beginPath();
    for(var i=0;i<data.length;i++){
      var x=p+(i/(data.length-1))*cw;
      var v=getVal(data[i]);
      var y=pt+ch-(v/maxVal)*ch;
      if(i===0)ctx.moveTo(x,y);
      else ctx.lineTo(x,y);
    }
    ctx.stroke();
  }

  drawLine(projData,lineColor,function(d){return d.end});
  drawLine(drawData.data,lineColor2,function(d){return d.start});

  ctx.fillStyle=lineColor;
  ctx.font='7px monospace';
  ctx.textAlign='center';
  if(projData.length>0){
    var last=projData[projData.length-1];
    ctx.fillText(fmtCurrency(last.end),p+cw,pt+ch+16);
  }

  ctx.fillStyle=textColor;
  ctx.font='7px monospace';
  ctx.textAlign='center';
  ctx.fillText('Age '+curAge,p,pt+ch+16);
  ctx.fillText('Retire '+retireAge,p+(retireAge-curAge)/((drawData.data.length?drawData.data[drawData.data.length-1].age:retireAge)-curAge)*cw,pt+ch+16);
}

function runMonteCarlo(nestEgg,curAge,retireAge,lifeExp,monthly,annReturn,stdDev,escRate,goalIncome,infl,includeSs,ssAmt,ssAge,wdStrategy,addIncomeMonthly,savings,expenses,tradNestEgg,retireTaxRate){
  var NUM_SIMS=2000;
  var rMean=annReturn/100,rStd=stdDev/100,iRate=infl/100,retireTaxDec=retireTaxRate/100,tradPct=parseFloat(taxPctEl.value||70)/100;
  var yearsToRetire=retireAge-curAge;
  var finalNestEggs=[];
  var successes=0;

  mcProbEl.textContent='Running...';
  mcProbEl.style.color='var(--color-info)';

  setTimeout(function(){
    for(var sim=0;sim<NUM_SIMS;sim++){
      var bal=savings;
      var curMonthly=monthly;

      for(var y=1;y<=yearsToRetire;y++){
        var randRet=rMean+rStd*gaussRandom();
        if(randRet<-0.5)randRet=-0.5;
        if(randRet>0.5)randRet=0.5;
        if(escRate>0&&y>1)curMonthly=monthly*Math.pow(1+escRate,y-1);
        bal+=curMonthly*12;
        bal+=bal*randRet;
      }

      var mcSsAmt=ssAmt,mcAddIncome=addIncomeMonthly;
      var mcSsAge=includeSs?ssAge:999;
      var initialEgg=bal;
      var mcBal=bal,mcTrad=bal*tradPct;
      var mcFirstWD=0;

      for(var age=retireAge;age<=lifeExp;age++){
        if(mcBal<=0)break;
        var mcYrAdd=mcAddIncome*12;
        var mcYrSs=age>=mcSsAge?mcSsAmt*12:0;
        var wdAge=age-retireAge+1;

        var mcYrInfo=calcDrawdownYear(mcBal,mcTrad,retireTaxDec,goalIncome,iRate,wdAge,wdStrategy,initialEgg,mcFirstWD,mcYrSs,mcYrAdd,expenses,age);
        mcFirstWD=mcYrInfo.firstYearWD;

        var totalDed=mcYrInfo.netWithdraw+mcYrInfo.taxOnWd+mcYrInfo.yrExpenses;
        var tradRed=Math.min(mcYrInfo.tradPortion+mcYrInfo.taxOnWd,mcTrad);
        mcTrad-=tradRed;if(mcTrad<0)mcTrad=0;
        mcBal-=totalDed;

        if(mcBal>0){
          var randRet2=rMean+rStd*gaussRandom();
          if(randRet2<-0.5)randRet2=-0.5;
          if(randRet2>0.5)randRet2=0.5;
          mcBal+=mcBal*randRet2;
          mcTrad+=mcTrad*randRet2;
        }
        if(mcSsAmt>0)mcSsAmt*=(1+iRate);
        if(mcAddIncome>0)mcAddIncome*=(1+iRate);
      }

      finalNestEggs.push(mcBal);
      if(mcBal>0)successes++;
    }

    var prob=(successes/NUM_SIMS*100);
    mcProbEl.textContent=prob.toFixed(1)+'%';
    mcProbEl.style.color=prob>=70?'var(--color-success)':prob>=40?'var(--color-warning)':'var(--color-error)';

    finalNestEggs.sort(function(a,b){return a-b});
    var p10=finalNestEggs[Math.floor(NUM_SIMS*0.1)]||0;
    var p25=finalNestEggs[Math.floor(NUM_SIMS*0.25)]||0;
    var p50=finalNestEggs[Math.floor(NUM_SIMS*0.5)]||0;
    var p75=finalNestEggs[Math.floor(NUM_SIMS*0.75)]||0;
    var p90=finalNestEggs[Math.floor(NUM_SIMS*0.9)]||0;

    mcP10.textContent=fmtCurrency(p10);
    mcP25.textContent=fmtCurrency(p25);
    mcP50.textContent=fmtCurrency(p50);
    mcP75.textContent=fmtCurrency(p75);
    mcP90.textContent=fmtCurrency(p90);

    drawMcDistribution(finalNestEggs,NUM_SIMS);
    toast('Monte Carlo complete — '+prob.toFixed(1)+'% success rate');
  },50);
}

function drawMcDistribution(values,numSims){
  var ctx=mcChart.getContext('2d');
  var W=mcChart.parentElement.clientWidth;
  var dpr=window.devicePixelRatio||1;
  var H=200;
  mcChart.width=W*dpr;
  mcChart.height=H*dpr;
  mcChart.style.width=W+'px';
  mcChart.style.height=H+'px';
  ctx.scale(dpr,dpr);

  var p=40,pt=20,pb=30;
  var cw=W-p*2,ch=H-pt-pb;

  ctx.clearRect(0,0,W,H);

  var textColor='rgba(255,255,255,0.35)';
  var gridColor='rgba(255,255,255,0.08)';
  try{
    var cs=getComputedStyle(document.documentElement);
    var pVal=cs.getPropertyValue('--p').trim();
    if(pVal)var barColor='hsl('+pVal+')';
    else barColor='hsl(221.2, 83.2%, 53.3%)';
    var erVal=cs.getPropertyValue('--er').trim();
    if(erVal)var erColor='hsl('+erVal+')';
    else erColor='hsl(0, 72.2%, 50.6%)';
    var suVal=cs.getPropertyValue('--su').trim();
    if(suVal)var suColor='hsl('+suVal+')';
    else suColor='hsl(158.6, 83.5%, 44.1%)';
  }catch(e){
    var barColor='hsl(221.2, 83.2%, 53.3%)';
    var erColor='hsl(0, 72.2%, 50.6%)';
    var suColor='hsl(158.6, 83.5%, 44.1%)';
  }

  var max=Math.max.apply(null,values);
  var min=Math.min.apply(null,values);
  var range=max-min||1;
  var numBins=Math.min(40,Math.max(10,Math.floor(Math.sqrt(numSims))));
  var binWidth=range/numBins;
  var bins=[];
  for(var i=0;i<numBins;i++)bins.push(0);
  values.forEach(function(v){
    var idx=Math.min(numBins-1,Math.floor((v-min)/binWidth));
    if(idx<0)idx=0;
    bins[idx]++;
  });
  var maxCount=Math.max.apply(null,bins)||1;

  ctx.strokeStyle=gridColor;
  ctx.lineWidth=0.5;
  ctx.fillStyle=textColor;
  ctx.font='8px monospace';
  ctx.textAlign='right';
  for(var i=0;i<=4;i++){
    var y=pt+ch-(ch/4)*i;
    ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(p+cw,y);ctx.stroke();
    ctx.fillText(Math.round(maxCount/4*i).toString(),p-4,y+3);
  }

  var barW=cw/numBins*0.8;
  var gap=cw/numBins*0.2;
  for(i=0;i<numBins;i++){
    var x=p+i*(barW+gap)+gap/2;
    var barH=(bins[i]/maxCount)*ch;
    var y=pt+ch-barH;
    var binVal=min+i*binWidth+binWidth/2;

    if(binVal<0)ctx.fillStyle=erColor;
    else if(bins[i]/maxCount>0.3)ctx.fillStyle=suColor;
    else ctx.fillStyle=barColor;

    ctx.fillRect(x,y,barW,barH);
  }

  if(min<0){
    var zeroX=p+(0-min)/range*cw;
    ctx.strokeStyle=erColor;
    ctx.lineWidth=1;
    ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(zeroX,pt);ctx.lineTo(zeroX,pt+ch);ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=erColor;
    ctx.font='7px monospace';
    ctx.textAlign='center';
    ctx.fillText('$0',zeroX,pt+ch+14);
  }

  ctx.fillStyle=textColor;
  ctx.font='7px monospace';
  ctx.textAlign='center';
  ctx.fillText(fmtCurrency(min),p,pt+ch+14);
  ctx.fillText(fmtCurrency(max),p+cw,pt+ch+14);
}

function goalSeek(){
  var curAge=parseFloat(ageEl.value)||0,
    retireAge=parseFloat(retireAgeEl.value)||65,
    lifeExp=parseFloat(lifeExpEl.value)||95,
    savings=parseFloat(savingsEl.value)||0,
    annReturn=parseFloat(returnEl.value)||7,
    infl=parseFloat(inflationEl.value)||3,
    escPct=parseFloat(escalationEl.value)||0,
    includeSs=ssToggle.checked,
    ssAmt=parseFloat(ssAmountEl.value)||0,
    ssAge=parseFloat(ssAgeEl.value)||67,
    pension=parseFloat(pensionEl.value)||0,
    rental=parseFloat(rentalEl.value)||0,
    partTime=parseFloat(partTimeEl.value)||0,
    goalIncome=parseFloat(goalIncomeEl.value)||0,
    wdStrategy=withdrawStrategyEl.value;

  if(curAge<=0||retireAge<=curAge){toast('Retirement age must be after your current age');return}
  if(goalIncome<=0){toast('Set a goal income first');return}

  gsResult.innerHTML='<div class="rp-gs-result"><div class="gs-v">Searching...</div></div>';

  setTimeout(function(){
    var lo=0,hi=100000,found=-1;
    for(var iter=0;iter<60;iter++){
      var mid=(lo+hi)/2;
      if(hi-lo<1){found=Math.ceil(mid);break}
      var testResult=simulateRetirement(mid);
      if(testResult)hi=mid;
      else lo=mid;
    }

    if(found>=0&&found<=100000){
      var actual=simulateRetirement(found);
      if(!actual){
        for(var j=found;j<=100000;j+=10){if(simulateRetirement(j)){found=j;break}}
      }
      monthlyEl.value=Math.round(found);
      gsResult.innerHTML='<div class="rp-gs-result"><div class="gs-v">'+fmtCurrency(Math.round(found))+'</div><div class="gs-l">Required monthly contribution to meet goal (auto-filled)</div></div>';
      toast('Goal seek complete');
    }else{
      gsResult.innerHTML='<div class="rp-gs-result" style="border-color:var(--color-error)"><div class="gs-v" style="color:var(--color-error)">Unreachable</div><div class="gs-l">Cannot meet goal — try adjusting inputs</div></div>';
    }
  },50);

  function simulateRetirement(testMonthly){
    var r=annReturn/100,iRate=infl/100,escRate=escPct/100;
    var yearsToRetire=retireAge-curAge;
    var bal=savings,curM=testMonthly;
    for(var y=1;y<=yearsToRetire;y++){
      if(escRate>0&&y>1)curM=testMonthly*Math.pow(1+escRate,y-1);
      bal+=curM*12;
      bal+=bal*r;
    }
    var addInc=pension+rental+partTime;
    var gsTaxPct=(parseFloat(taxPctEl.value)||70)/100;
    var dd=projectDrawdown(bal,annReturn,goalIncome,infl,includeSs,ssAmt,ssAge,retireAge,lifeExp,wdStrategy,addInc,[],bal*gsTaxPct,parseFloat(retireTaxRateEl.value||15));
    return dd.avgMonthly>=goalIncome&&dd.years>=(lifeExp-retireAge);
  }
}

function exportCsv(type){
  if(type==='proj'&&(!lastProjData1||!lastProjData1.length)){toast('Calculate first');return}
  if(type==='draw'&&(!lastDrawData1||!lastDrawData1.data.length)){toast('Calculate first');return}

  var lines=[],filename;
  if(type==='proj'){
    lines.push('Age,Year,Start,Contributions,Growth,End');
    lastProjData1.forEach(function(d){
      lines.push(d.age+','+d.year+','+Math.round(d.start)+','+Math.round(d.contrib)+','+Math.round(d.growth)+','+Math.round(d.end));
    });
    filename='retirement-projection-'+Date.now()+'.csv';
  }else{
    lines.push('Age,Year,Start Balance,Withdrawal,Tax,Social Security,Additional Income,Growth,End Balance');
    lastDrawData1.data.forEach(function(d,i){
      lines.push(d.age+','+(i+1)+','+Math.round(d.start)+','+Math.round(d.withdraw)+','+Math.round(d.tax||0)+','+Math.round(d.ss)+','+Math.round(d.additional)+','+Math.round(d.growth)+','+Math.round(d.end));
    });
    filename='retirement-drawdown-'+Date.now()+'.csv';
  }

  var b=new Blob([lines.join('\n')],{type:'text/csv;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=filename;a.click();URL.revokeObjectURL(a.href);
  toast('CSV downloaded');
}

function copyAll(){
  var curAge=parseFloat(ageEl.value)||0,retireAge=parseFloat(retireAgeEl.value)||65,lifeExp=parseFloat(lifeExpEl.value)||95;
  var savings=parseFloat(savingsEl.value)||0,monthly=parseFloat(monthlyEl.value)||0,annRet=parseFloat(returnEl.value)||7;
  var infl=parseFloat(inflationEl.value)||3,esc=parseFloat(escalationEl.value)||0;
  var includeSs=ssToggle.checked,ssAmt=parseFloat(ssAmountEl.value)||0,ssAge=parseFloat(ssAgeEl.value)||67;
  var goal=parseFloat(goalIncomeEl.value)||0;
  var txt='=== Retirement Planning Report ===\nDate: '+new Date().toISOString().slice(0,10)+'\n\nInputs:\nCurrent Age: '+curAge+'\nRetirement Age: '+retireAge+'\nLife Expectancy: '+lifeExp+'\nSavings: '+fmtCurrency(savings)+'\nMonthly Contribution: '+fmtCurrency(monthly)+'\nAnnual Return: '+annRet+'%\nInflation: '+infl+'%\nEscalation: '+esc+'%\nSocial Security: '+(includeSs?fmtCurrency(ssAmt)+'/mo at age '+ssAge:'No')+'\nGoal Income: '+(goal>0?fmtCurrency(goal)+'/mo':'Not set')+'\n\nResults:\nNest Egg: '+nestEggEl.textContent+'\nTotal Contributions: '+totalContribEl.textContent+'\nInvestment Growth: '+totalGrowthEl.textContent+'\nEst. Monthly Income: '+monthlyIncomeEl.textContent+'\nFunds Last: '+runwayEl.textContent+'\nGoal: '+goalStatusEl.querySelector('.sv').textContent;
  navigator.clipboard.writeText(txt).then(function(){toast('Copied!')}).catch(function(){toast('Copy failed')});
}

function dlReport(){
  var curAge=parseFloat(ageEl.value)||0,retireAge=parseFloat(retireAgeEl.value)||65,lifeExp=parseFloat(lifeExpEl.value)||95;
  var savings=parseFloat(savingsEl.value)||0,monthly=parseFloat(monthlyEl.value)||0,annRet=parseFloat(returnEl.value)||7;
  var infl=parseFloat(inflationEl.value)||3,esc=parseFloat(escalationEl.value)||0;
  var includeSs=ssToggle.checked,ssAmt=parseFloat(ssAmountEl.value)||0,ssAge=parseFloat(ssAgeEl.value)||67;
  var goal=parseFloat(goalIncomeEl.value)||0;
  var txt='=== Retirement Planning Report ===\nDate: '+new Date().toISOString().slice(0,10)+'\n\nInputs:\nCurrent Age: '+curAge+'\nRetirement Age: '+retireAge+'\nLife Expectancy: '+lifeExp+'\nSavings: '+fmtCurrency(savings)+'\nMonthly Contribution: '+fmtCurrency(monthly)+'\nAnnual Return: '+annRet+'%\nInflation: '+infl+'%\nEscalation: '+esc+'%\nSocial Security: '+(includeSs?fmtCurrency(ssAmt)+'/mo at age '+ssAge:'No')+'\nGoal Income: '+(goal>0?fmtCurrency(goal)+'/mo':'Not set')+'\n\nResults:\nNest Egg: '+nestEggEl.textContent+'\nTotal Contributions: '+totalContribEl.textContent+'\nInvestment Growth: '+totalGrowthEl.textContent+'\nEst. Monthly Income: '+monthlyIncomeEl.textContent+'\nFunds Last: '+runwayEl.textContent+'\nGoal: '+goalStatusEl.querySelector('.sv').textContent+'\n\n---\nstorybrainai.com/tool/retirement-planning-calculator';
  var b=new Blob([txt],{type:'text/plain;charset=utf-8'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='retirement-plan-'+Date.now()+'.txt';a.click();URL.revokeObjectURL(a.href);toast('Downloaded');
}

function saveHistory(curAge,retireAge,lifeExp,savings,monthly,annRet,infl,esc,includeSs,ssAmt,ssAge,goal,nestEgg,monthlyInc,yearsLast){
  var label=curAge+'yr, '+fmtCurrency(monthly)+'/mo, retire '+retireAge;
  history.unshift({
    curAge:curAge,retireAge:retireAge,lifeExp:lifeExp,savings:savings,monthly:monthly,annReturn:annRet,
    inflation:infl,escalation:esc,includeSs:includeSs,ssAmt:ssAmt,ssAge:ssAge,goal:goal,
    nestEgg:nestEgg,monthlyIncome:monthlyInc,yearsLast:yearsLast,label:label,ts:Date.now()
  });
  if(history.length>30)history.pop();
  try{localStorage.setItem(HIST_KEY,JSON.stringify(history))}catch(e){}
  renderHistory();
}

function renderHistory(){
  hiCount.textContent=history.length?'('+history.length+')':'';hiClear.hidden=!history.length;
  if(!history.length){hiList.innerHTML='<div class="rp-empty">No calculations yet</div>';return}
  var h='';
  history.forEach(function(item,i){
    var d2=new Date(item.ts),diff=Math.round((Date.now()-d2)/1000);
    var rel=diff<60?'now':diff<3600?Math.floor(diff/60)+'m':diff<86400?Math.floor(diff/3600)+'h':Math.floor(diff/86400)+'d';
    h+='<div class="rp-hist-item" data-idx="'+i+'"><span class="preview">'+esc(item.label)+'</span><span class="meta">'+rel+'</span><button type="button" class="hdel" data-idx="'+i+'" aria-label="Delete">\u2715</button></div>';
  });
  hiList.innerHTML=h;
}

ccyEl.addEventListener('change',function(){
  currentCurrency=ccyEl.value;
  try{localStorage.setItem('sb_rp_ccy',currentCurrency)}catch(e){}
  if(!resultsDiv.hidden&&lastProjData1)runCalc(false);
});

ssToggle.addEventListener('change',function(){document.getElementById('rpSsFields').style.opacity=ssToggle.checked?'1':'.3'});

var tabs=document.getElementById('rpTabs'),sections={};
['overview','projection','drawdown','montecarlo','compare'].forEach(function(t){sections[t]=document.getElementById('rpTab'+t.charAt(0).toUpperCase()+t.slice(1))});
tabs.addEventListener('click',function(e){
  var b=e.target.closest('button[data-tab]');if(!b)return;
  var tab=b.getAttribute('data-tab');
  tabs.querySelectorAll('button').forEach(function(el){el.classList.toggle('on',el.getAttribute('data-tab')===tab);el.setAttribute('aria-selected',el.getAttribute('data-tab')===tab)});
  Object.keys(sections).forEach(function(k){sections[k].classList.toggle('active',k===tab)});
});

hiToggle.addEventListener('click',function(){var o=hiToggle.getAttribute('aria-expanded')==='true';hiToggle.setAttribute('aria-expanded',!o);hiWrap.hidden=o;hiToggle.classList.toggle('on');if(!o)renderHistory()});
hiClear.addEventListener('click',function(){history=[];try{localStorage.setItem(HIST_KEY,JSON.stringify(history))}catch(e){}renderHistory();toast('Cleared')});
hiList.addEventListener('click',function(e){
  var del=e.target.closest('.hdel');if(del){var idx=parseInt(del.getAttribute('data-idx'));history.splice(idx,1);try{localStorage.setItem(HIST_KEY,JSON.stringify(history))}catch(e){}renderHistory();return}
  var item=e.target.closest('.rp-hist-item');if(!item)return;
  var idx=parseInt(item.getAttribute('data-idx')),h=history[idx];if(!h)return;
  ageEl.value=h.curAge;retireAgeEl.value=h.retireAge;lifeExpEl.value=h.lifeExp;
  savingsEl.value=h.savings;monthlyEl.value=h.monthly;returnEl.value=h.annReturn;
  inflationEl.value=h.inflation;escalationEl.value=h.escalation;
  ssToggle.checked=h.includeSs;ssAmountEl.value=h.ssAmt||0;ssAgeEl.value=h.ssAge||67;
  goalIncomeEl.value=h.goal||0;
  document.getElementById('rpSsFields').style.opacity=h.includeSs?'1':'.3';
  history.splice(idx,1);try{localStorage.setItem(HIST_KEY,JSON.stringify(history))}catch(e){}renderHistory();runCalc(false);toast('Restored');
});

calcBtn.addEventListener('click',function(){runCalc(false)});
mcBtn.addEventListener('click',function(){
  if(lastNestEgg1>0)runMonteCarlo(lastNestEgg1,lastCurAge,lastRetireAge,lastLifeExp,parseFloat(monthlyEl.value)||0,parseFloat(returnEl.value)||7,parseFloat(stdDevEl.value)||15,(parseFloat(escalationEl.value)||0)/100,parseFloat(goalIncomeEl.value)||0,(parseFloat(inflationEl.value)||0)/100,ssToggle.checked,parseFloat(ssAmountEl.value)||0,parseFloat(ssAgeEl.value)||67,withdrawStrategyEl.value,(parseFloat(pensionEl.value)||0)+(parseFloat(rentalEl.value)||0)+(parseFloat(partTimeEl.value)||0),parseFloat(savingsEl.value)||0,getExpenses(),lastNestEgg1*(parseFloat(taxPctEl.value||70)/100),parseFloat(retireTaxRateEl.value||15));
  else toast('Calculate first');
});
copyBtn.addEventListener('click',copyAll);
dlBtn.addEventListener('click',dlReport);
gsBtn.addEventListener('click',goalSeek);
csvProjBtn.addEventListener('click',function(){exportCsv('proj')});
csvDrawBtn.addEventListener('click',function(){exportCsv('draw')});

window.addEventListener('resize',function(){
  if(lastProjData1&&lastDrawData1)drawProjectionChart(lastProjData1,lastDrawData1,lastCurAge,lastRetireAge,lastNestEgg1);
});

updateTaxBar();
runCalc(false);
})();
