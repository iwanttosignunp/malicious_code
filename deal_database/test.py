import requests
import yaml
import os
import json
import time

def load_config():
    # 读取同级或上级目录的 settings.yaml
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(base_dir, 'settings.yaml')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_test(name, payload, url):
    print(f"\n{'='*20} {name} {'='*20}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Time Elapsed: {elapsed:.4f}s")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Message: {result.get('message')}")
            data = result.get('data', [])
            print(f"Results Count: {len(data)}")
            
            # 简略打印结果
            if data:
                print("\n--- Top Results Preview ---")
                # Handle both list of lists (parallel) and single list (if logic changes, but current logic returns List[List])
                # Current search.py always returns List[List] for 'vector_search' with our changes?
                # Let's check the logic: queries = [...] ... results_list = executor.map ...
                # yes, it returns a list of results for each query.
                
                for q_idx, entry in enumerate(data):
                    print(f"\nQuery {q_idx + 1} Results:")
                    
                    # 兼容新旧格式：新格式为 dict {'input_code':..., 'matches':...}，旧格式为 list
                    if isinstance(entry, dict):
                        matches = entry.get('records', [])
                    elif isinstance(entry, list):
                        matches = entry
                    else:
                        matches = []

                    if not matches:
                        print("  (No matches)")
                        continue
                        
                    for r_idx, item in enumerate(matches[:2]): # Show top 2
                        print(f"  Rank {r_idx+1}:")
                        print(f"    Title: {item.get('title')}")
                        print(f"    File:  {item.get('file_name')}")
                        print(f"    Dist:  {item.get('_additional', {}).get('distance', 'N/A'):.4f}")
                        print(f"    Cert:  {item.get('_additional', {}).get('certainty', 'N/A'):.4f}")
                        code = item.get('code', '') or ''
                        # 截取并在缩进显示代码
                        code_preview = code[:200].replace('\n', '\n        ')
                        print(f"    Code:  {code_preview}...")
        else:
            print("Error Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {url}. Is the server running?")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # 1. 加载配置
    config = load_config()
    vector_conf = config.get('vector_search', {})
    host = vector_conf.get('host', '0.0.0.0')
    port = vector_conf.get('port', 5127)
    
    # localhost fallback if 0.0.0.0
    if host == "0.0.0.0":
        host = "127.0.0.1"
        
    api_url = f"http://{host}:{port}/vector_search"
    
#     payload_list = {
#         "query_code": ["""void FUN_10002580(HMODULE param_1,undefined4 param_2)

# {
#   ushort uVar1;
#   char cVar2;
#   BOOL BVar3;
#   HANDLE hObject;
#   int iVar4;
#   uint uVar5;
#   ushort *puVar6;
#   ushort *puVar7;
#   void *pvVar8;
#   bool bVar9;
#   undefined *puVar10;
#   undefined4 local_270 [9];
#   ushort local_24c [260];
#   _SYSTEM_INFO local_44;
#   undefined8 local_20;
#   int local_18;
#   uint local_14;
#   void *local_10;
#   undefined1 *puStack_c;
#   undefined4 local_8;
  
#   local_8 = 0xffffffff;
#   puStack_c = &LAB_10004cad;
#   local_10 = ExceptionList;
#   local_14 = DAT_10008004 ^ (uint)&stack0xfffffffc;
#   ExceptionList = &local_10;
#   switch(param_2) {
#   case 0:
#     puVar10 = &DAT_10005a14;
#     break;
#   case 1:
#     FUN_100012a0(&DAT_100058ec);
#     FUN_100012a0(&DAT_100058f8);
#     cVar2 = FUN_10002180();
#     if (cVar2 == '\0') {
#       BVar3 = IsDebuggerPresent();
#       FUN_100012a0(&DAT_100056ec);
#       if (BVar3 == 0) {
#         cVar2 = FUN_10001e80();
#         if (cVar2 == '\0') {
#           FUN_100012a0(&DAT_10005928);
#         }
#         else {
#           GetSystemInfo(&local_44);
#           FUN_100012a0(&DAT_10005634);
#           if (local_44.dwNumberOfProcessors < 4) {
#             FUN_100012a0(&DAT_10005938);
#           }
#           else {
#             cVar2 = FUN_10002410();
#             if (cVar2 == '\0') {
#               FUN_100012a0(&DAT_1000594c);
#             }
#             hObject = (HANDLE)CreateToolhelp32Snapshot(2,0);
#             if (hObject != (HANDLE)0xffffffff) {
#               local_270[0] = 0x22c;
#               iVar4 = Process32FirstW(hObject,local_270);
#               while (iVar4 != 0) {
#                 puVar7 = &DAT_1000595c;
#                 puVar6 = local_24c;
#                 do {
#                   uVar1 = *puVar6;
#                   bVar9 = uVar1 < *puVar7;
#                   if (uVar1 != *puVar7) {
# LAB_10002726:
#                     uVar5 = -(uint)bVar9 | 1;
#                     goto LAB_1000272b;
#                   }
#                   if (uVar1 == 0) break;
#                   uVar1 = puVar6[1];
#                   bVar9 = uVar1 < puVar7[1];
#                   if (uVar1 != puVar7[1]) goto LAB_10002726;
#                   puVar6 = puVar6 + 2;
#                   puVar7 = puVar7 + 2;
#                 } while (uVar1 != 0);
#                 uVar5 = 0;
# LAB_1000272b:
#                 if (uVar5 == 0) {
#                   FUN_100012a0(&DAT_1000596c);
#                 }
#                 puVar7 = &DAT_10005780;
#                 puVar6 = local_24c;
#                 do {
#                   uVar1 = *puVar6;
#                   bVar9 = uVar1 < *puVar7;
#                   if (uVar1 != *puVar7) {
# LAB_10002776:
#                     uVar5 = -(uint)bVar9 | 1;
#                     goto LAB_1000277b;
#                   }
#                   if (uVar1 == 0) break;
#                   uVar1 = puVar6[1];
#                   bVar9 = uVar1 < puVar7[1];
#                   if (uVar1 != puVar7[1]) goto LAB_10002776;
#                   puVar6 = puVar6 + 2;
#                   puVar7 = puVar7 + 2;
#                 } while (uVar1 != 0);
#                 uVar5 = 0;
# LAB_1000277b:
#                 if (uVar5 == 0) {
#                   FUN_100012a0(&DAT_10005980);
#                 }
#                 iVar4 = Process32NextW(hObject,local_270);
#               }
#               CloseHandle(hObject);
#             }
#             cVar2 = FUN_10001f30();
#             if (cVar2 == '\0') {
#               FUN_100012a0(&DAT_100059ac);
#             }
#             local_20 = 0;
#             local_18 = 0;
#             local_8 = 0;
#             cVar2 = FUN_100016b0((int *)&local_20);
#             if (cVar2 == '\0') {
#               puVar10 = &DAT_100059e0;
#             }
#             else {
#               cVar2 = FUN_10001b20((int *)&local_20);
#               puVar10 = &DAT_100059c0;
#               if (cVar2 != '\0') {
#                 puVar10 = &DAT_100059cc;
#               }
#             }
#             FUN_100012a0(puVar10);
#             DisableThreadLibraryCalls(param_1);
#             CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,FUN_100020f0,(LPVOID)0x0,0,(LPDWORD)0x0);
#             if ((void *)local_20 != (void *)0x0) {
#               pvVar8 = (void *)local_20;
#               if ((0xfff < (uint)(local_18 - (int)(void *)local_20)) &&
#                  (pvVar8 = *(void **)((int)(void *)local_20 + -4),
#                  0x1f < (uint)((int)(void *)local_20 + (-4 - (int)pvVar8)))) {
#                     /* WARNING: Subroutine does not return */
#                 _invalid_parameter_noinfo_noreturn();
#               }
#               FUN_10003e6e(pvVar8);
#             }
#           }
#         }
#       }
#       else {
#         FUN_100012a0(&DAT_10005914);
#       }
#     }
#     else {
#       FUN_100012a0(&DAT_10005904);
#     }
#     goto switchD_100025bd_default;
#   case 2:
#     puVar10 = &DAT_100059fc;
#     break;
#   case 3:
#     puVar10 = &DAT_10005a08;
#     break;
#   default:
#     goto switchD_100025bd_default;
#   }
#   FUN_100012a0(puVar10);
# switchD_100025bd_default:
#   ExceptionList = local_10;
#   FUN_10003e30(local_14 ^ (uint)&stack0xfffffffc);
#   return;
# }
# """, """BVar3 = IsDebuggerPresent();
# FUN_100012a0(&DAT_100056ec);
# if (BVar3 == 0) {
#   cVar2 = FUN_10001e80();
#   if (cVar2 == '\0') {
#     FUN_100012a0(&DAT_10005928);
#   }
# }
# else {
#   GetSystemInfo(&local_44);
#   FUN_100012a0(&DAT_10005634);
#   if (local_44.dwNumberOfProcessors < 4) {
#     FUN_100012a0(&DAT_10005938);
#   }
#   else {
#     cVar2 = FUN_10002410();
#     if (cVar2 == '\0') {
#       FUN_100012a0(&DAT_1000594c);
#     }
#   }
#   hObject = (HANDLE)CreateToolhelp32Snapshot(2,0);
#   if (hObject != (HANDLE)0xffffffff) {
#     local_270[0] = 0x22c;
#     iVar4 = Process32FirstW(hObject,local_270);
#     while (iVar4 != 0) {
#       puVar7 = &DAT_1000595c;
#       puVar6 = local_24c;
#       do {
#         uVar1 = *puVar6;
#         bVar9 = uVar1 < *puVar7;
#         if (uVar1 != *puVar7) {"""]
#     }
    payload_list = {
            "query_code": ["""BVar3 = IsDebuggerPresent();
if (BVar3 == 0) {
  hObject = (HANDLE)CreateToolhelp32Snapshot(2,0);
  if (hObject != (HANDLE)0xffffffff) {
    local_270[0] = 0x22c;
    iVar4 = Process32FirstW(hObject,local_270);
    while (iVar4 != 0) {
      puVar7 = &DAT_1000595c;
      puVar6 = local_24c;
      do {
        uVar1 = *puVar6;
        bVar9 = uVar1 < *puVar7;
        if (uVar1 != *puVar7) {
          uVar5 = -(uint)bVar9 | 1;
          goto LAB_1000272b;
        }
        if (uVar1 == 0) break;
        uVar1 = puVar6[1];
        bVar9 = uVar1 < puVar7[1];
        if (uVar1 != puVar7[1]) goto LAB_10002726;
        puVar6 = puVar6 + 2;
        puVar7 = puVar7 + 2;
      } while (uVar1 != 0);
      uVar5 = 0;
LAB_1000272b:
      if (uVar5 == 0) {
        FUN_100012a0(&DAT_1000596c);
      }
      puVar7 = &DAT_10005780;
      puVar6 = local_24c;
      do {
        uVar1 = *puVar6;
        bVar9 = uVar1 < *puVar7;
        if (uVar1 != *puVar7) {
          uVar5 = -(uint)bVar9 | 1;
          goto LAB_1000277b;
        }
        if (uVar1 == 0) break;
        uVar1 = puVar6[1];
        bVar9 = uVar1 < puVar7[1];
        if (uVar1 != puVar7[1]) goto LAB_10002776;
        puVar6 = puVar6 + 2;
        puVar7 = puVar7 + 2;
      } while (uVar1 != 0);
      uVar5 = 0;
LAB_1000277b:
      if (uVar5 == 0) {
        FUN_100012a0(&DAT_10005980);
      }
      iVar4 = Process32NextW(hObject,local_270);
    }
    CloseHandle(hObject);
  }
}
CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,FUN_100020f0,(LPVOID)0x0,0,(LPDWORD)0x0);
"""]
    }
    run_test("List Query (Parallel)", payload_list, api_url)
