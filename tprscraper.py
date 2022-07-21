import os,sys,datetime,csv,colorama,bs4
from districts_map import state_code_to_name,state_name_to_code,state_names_caps,district_to_state,state_to_district,duplicated_districts

def highlight(text):
    highlight_begin = colorama.Back.BLACK + colorama.Fore.WHITE + colorama.Style.BRIGHT
    highlight_reset = (
        colorama.Back.RESET + colorama.Fore.RESET + colorama.Style.RESET_ALL
    )
    return highlight_begin + text + highlight_reset

def scrape_download_mohfw_website():
  date = datetime.datetime.now().strftime("%Y-%m-%d")
  if os.path.exists('index.html'): os.remove('index.html')
  
  cmd='wget https://mohfw.gov.in/ -O index.html';
  print(cmd);os.system(cmd);
  
  soup=bs4.BeautifulSoup(open('index.html'),'html.parser')
  spreadsheet_links=list(set([i['href'] for i in soup('a') if i.has_attr('href') and '.xlsx' in i['href'] and 'tivity' in i['href']]))
  if not spreadsheet_links:
    print(highlight('Could not find Weekly district-wise +vity spreadsheet (.xlsx) from https://mohfw.gov.in/ on %s!!' %(date)))
    return
  basename=os.path.split(spreadsheet_links[0])[1]
  fname='mohfw_spreadsheets_archive/2022/'+basename
  if os.path.exists(fname):
    print('File %s already exists in archive\nSkipping!!\n------------' %(fname))
  else:
    print('File %s does not exist in archive\nDownloading!\n------------' %(fname))
    cmd='wget "'+spreadsheet_links[0]+'" -O "'+fname+'"'
    print(cmd);os.system(cmd);
    #update csv
    scraper(fname,write_csv=True)
    
  
def scraper(infile='COVID19DistrictWisePositivityAnalysis20July.xlsx',year=2022,write_csv=False):
  print_info=''
  if os.path.exists('tmp.csv'): os.remove('tmp.csv')
  cmd='xlsx2csv "'+infile+'" tmp.csv';
  os.system(cmd)
  
  #override year using __ in fname 
  if '__' in os.path.split(infile)[1]:    
    year_from_special_fname=int(os.path.split(infile)[1].replace('.xlsx','').split('__')[-1])    
    if year_from_special_fname!=year:
      print_info+='overriding default/given year: %d, with year from mtime: %d' %(year,year_from_special_fname)
      year=year_from_special_fname
  
  b=[i.strip()[1:] for i in open('tmp.csv').readlines() if i.strip()]
  
  #get date
  start_date='';end_date='';
  for i in b:
    if (len(i.split(',')[0].split())==5) and ('to' in i.split(',')[0].split()): 
      date_str=i.split(',')[0].split();
      d1=date_str[0].replace('st','').replace('nd','').replace('rd','').replace('th','')+' '+date_str[1]+' '+str(year)
      start_date=datetime.datetime.strptime(d1,'%d %B %Y').strftime('%Y-%m-%d')
      d2=date_str[3].replace('st','').replace('nd','').replace('rd','').replace('th','')+' '+date_str[4]+' '+str(year)
      end_date=datetime.datetime.strptime(d2,'%d %B %Y').strftime('%Y-%m-%d')
      print_info+='\nspreadsheet: %s , date: %s to %s' %(infile,start_date,end_date)
      break
  #get start of dataset
  r=csv.reader(open('tmp.csv'));  info=[i for i in r]
  
  for i in range(len(info)):
    if info[i][1]=='1': 
      info=info[i:];break
  
  #extract data
  info2=[]
  for y in info:
    y=[i for i in y if i and (i not in state_names_caps)]
    if y: 
      # ~ y=y[1:]
      
      #detect district names
      for j in range(len(y)):
        col=y[j]
        if col.replace(' ','').isalpha() and col.lower().strip()!='grand total': #ignore grand total fields though
          # ~ pass
          try:
          #next 3 fields are rat_fraction,pcr_fraction,net_district_tpr
            fields=y[j+1:j+4]
            if fields:
              rat_fraction,pcr_fraction,net_district_tpr=fields
              rat_fraction=float(rat_fraction.replace('-','0'))
              pcr_fraction=float(pcr_fraction.replace('-','0'))
              net_district_tpr=float(net_district_tpr.replace('-','0'))
              info2.append((col,rat_fraction,pcr_fraction,net_district_tpr))
            else:
              print_info+='\n'+highlight('empty fields for district: %s . continuing' %(col))
  
            
          except:
            print_info+='\n'+highlight('Failed to parse rat_fraction,pcr_fraction,net_district_tpr fields for district: %s. Fields were %s!!\nreturning!!' %(col,str(y[j+1:j+4])))
            # ~ return
            
  out=[]
  for i in info2:
    (district,rat_fraction,pcr_fraction,net_district_tpr)=i
    try:
      if district in duplicated_districts: #handle separately
        if district=='AURANGABAD': #call both mh, then check at end
          state_name="Maharashtra".upper()
        elif  district in ['BALRAMPUR','HAMIRPUR']: #call both up, then check at end
          state_name="Uttar Pradesh".upper()
        out.append([start_date,end_date,state_name,district,rat_fraction,pcr_fraction,net_district_tpr])
      else:
        state_name=state_code_to_name[district_to_state[district]].upper()
        out.append([start_date,end_date,state_name,district,rat_fraction,pcr_fraction,net_district_tpr])
    except:
      print_info+='\nCould not find state name for district: %s ! continuing!' %(district)
      continue
  out.sort()
  
 
  #fix duplicate districts heurisitics!  
 
  #AURANGABAD: district with higher pcr fraction is assumed to be in MH, else BR
  aurg_idx=[j for j in range(len(out)) if out[j][3]=='AURANGABAD']
  if aurg_idx:
    if out[aurg_idx[0]][5]>=out[aurg_idx[1]][5]: out[aurg_idx[1]][2]='BIHAR'
    else: out[aurg_idx[0]][0]='BIHAR'
  
  #BALRAMPUR: district with higher pcr fraction is assumed to be in UP, else CT
  aurg_idx=[j for j in range(len(out)) if out[j][3]=='BALRAMPUR']
  if aurg_idx:
    if out[aurg_idx[0]][5]>=out[aurg_idx[1]][5]: out[aurg_idx[1]][2]="Chhattisgarh".upper()
    else: out[aurg_idx[0]][0]="Chhattisgarh".upper()
  
  #HAMIRPUR: district with higher pcr fraction is assumed to be in UP, else HP
  aurg_idx=[j for j in range(len(out)) if out[j][3]=='HAMIRPUR']
  if aurg_idx:
    if out[aurg_idx[0]][5]>=out[aurg_idx[1]][5]: out[aurg_idx[1]][2]="Himachal Pradesh".upper()
    else: out[aurg_idx[0]][0]="Himachal Pradesh".upper()
  
  if write_csv:
    a=open('india_districts_tpr.csv','a');w=csv.writer(a)
    w.writerows(out)
    a.close()
    #remove duplicate entries
    cmd='head -n1 india_districts_tpr.csv > 22;sed -i "1,1d" india_districts_tpr.csv;cat india_districts_tpr.csv |sort -uk1 >> 22;mv -f 22 india_districts_tpr.csv'
    os.system(cmd)
    
  #cleanup tmp files before existing
  if os.path.exists('tmp.csv'): os.remove('tmp.csv')
  
  print(print_info)
  return out
if __name__=='__main__':
  if len(sys.argv)>1:
    if sys.argv[1] in ["scrape_download_mohfw_website"]:
      scrape_download_mohfw_website()
    elif sys.argv[1] in ["scraper"]:
      if os.path.exists(sys.argv[-1]):
        scraper(sys.argv[-1])
    else:
      if os.path.exists(sys.argv[-1]):
        scraper(sys.argv[-1])
