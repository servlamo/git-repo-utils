import json
import urllib.request
import ssl
import subprocess
import shlex
from urllib.error import HTTPError, URLError
import time
import sys
import yaml

printLog = "debug"


def _sendUrlRequest(url, sslCheck, headers, data=None, method='GET'):
    """
    Выполняет запрос к URL Gitlab сервера
    """
    result = {
        "name": url,
        "changes": {},
        "status": False,
        "comment": "",
        "out": {},
        "response": {}
    }
    global printLog
    debug_message = """ Query params:
                url: {url}
                sslCheck: {sslCheck}
                method: {method}
                headers: {headers}
                data: {data} """.format(
        url=url,
        sslCheck=sslCheck,
        method=method,
        headers=headers,
        data=data
    )
    if printLog == "all" or printLog == "trace":
        print(debug_message)
    try:
        if not sslCheck:
            ssl._create_default_https_context = ssl._create_unverified_context
        request = urllib.request.Request(
                                         url,
                                         data=data,
                                         headers=headers,
                                         method=method
        )
        response = urllib.request.urlopen(request)
        result["out"] = json.loads(response.read())
        result["status"] = True
        result["comment"] = "HTTP запрос выполнен успешно"
        result["response"] = response
    except (HTTPError, URLError) as err:
        message = \
            "Невозможно получить данные по url: {}. ERROR: {}".format(url, err)
        result["status"] = False
        result["comment"] = message
        print(message)
    return result


def _getFirstLevelSubGroups(prefixUrl, groupId, token):
    """
    Возвращает  json со списоком подгрупп первого уровня в поле out
    """
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Получаем список подгрупп для групп id " + groupId)
    url = prefixUrl + "groups/" + groupId + "/subgroups?" + \
        "pagination=keyset&per_page=100&order_by=name&sort=asc"
    result = {
        "name": url,
        "changes": {},
        "status": False,
        "comment": "",
        "out": []
    }
    h_dict_str = '{"Content-Type":"application/json","Authorization":"Bearer '\
                 + token + '"}'
    headers = json.loads(h_dict_str)
    resQuery = _sendUrlRequest(
        url,
        sslCheck=False,
        data=None,
        method='GET',
        headers=headers
    )
    result["comment"] = resQuery["comment"]
    if resQuery["status"]:
        numberPages = resQuery["response"].getheader('X-Total-Pages')
        print("Количество полученных страниц:" + numberPages)
        result["status"] = True
        if numberPages == "1":
            for group in resQuery["out"]:
                result["out"].append(str(group["name"]))
        else:
            url = prefixUrl + "groups/" + groupId + "/subgroups?" + \
                "pagination=keyset&per_page=100&order_by=name&sort=asc"
            resQuery = _sendUrlRequest(
                url,
                sslCheck=False,
                data=None,
                method='GET',
                headers=headers
            )
            for group in resQuery["out"]:
                result["out"].append(str(group["name"]))
        if printLog == "all" or printLog == "debug" or printLog == "trace":
            dt = time.ctime()
            print(dt + " Список подгрупп для групп id " + groupId + ":")
            print( result["out"] )
    else:
        result["status"] = False
    return result


def _getGroupProjects(prefixUrl, groupId, token):
    """
    Возвращает  json со списоком проектов первого уровня в поле out
    """
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Получаем список репозиториев для групп id " + groupId)
    url = prefixUrl + "groups/" + groupId + \
        "/projects?pagination=keyset&per_page=100&order_by=name&sort=asc"
    result = {
        "name": url,
        "changes": {},
        "status": False,
        "comment": "",
        "out": []
    }
    h_dict_str = '{"Content-Type":"application/json","Authorization":"Bearer '\
                 + token + '"}'
    headers = json.loads(h_dict_str)
    resQuery = _sendUrlRequest(
        url,
        sslCheck=False,
        data=None,
        method='GET',
        headers=headers
    )
    result["comment"] = resQuery["comment"]
    if resQuery["status"]:
        numberPages = resQuery["response"].getheader('X-Total-Pages')
        result["status"] = True
        if numberPages == "1":
            for group in resQuery["out"]:
                result["out"].append(str(group["name"]))
        else:
            url = prefixUrl + "groups/" + groupId + "/projects?" + \
                "pagination=keyset&per_page=100&order_by=name&sort=asc"
            resQuery = _sendUrlRequest(
                url,
                sslCheck=False,
                data=None,
                method='GET',
                headers=headers
            )
            for group in resQuery["out"]:
                result["out"].append(str(group["name"]))
        if printLog == "all" or printLog == "debug" or printLog == "trace":
            dt = time.ctime()
            print(dt + " Список подгрупп для групп id " + groupId + ":")
            print( result["out"] )
    else:
        result["status"] = False
    return result


def _subGroupExists(prefixUrl, groupId, groupName, token):
    """
    Возвращает True если подгруппа существует
    """
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Проверка существования подгруппы с именем " + groupName + " в группе с id: " + groupId)
    result = {
        "name": groupName,
        "changes": {},
        "status": False,
        "comment": " Подгруппа с именем " + groupName + " в группе с  id: " + groupId + " не существует",
        "out": {}
    }
    resQuery = _getFirstLevelSubGroups(prefixUrl, groupId, token)
    if resQuery["status"]:
        for group in resQuery["out"]:
            if group == groupName:
                result["comment"] = "SubGroup exists"
                result["status"] = True
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " Подгруппа с именем " + groupName + " в группе с  id: " + groupId + " существует")
                return result
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Подгруппа с именем " + groupName + " в группе с  id: " + groupId + " не существует")
    return result


def _projectExists(prefixUrl, groupId, projectName, token):
    """
    Возвращает True в поле status если проект существует
    """
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Проверка существования репозитория с именем " + projectName + " в группе с id: " + groupId)
    result = {
        "name": projectName,
        "changes": {},
        "status": False,
        "comment": " Репозиторий с именем " + projectName + " в группе с  id: " + groupId + " не существует",
        "out": {}
    }
    resQuery = _getGroupProjects(prefixUrl, groupId, token)
    if resQuery["status"]:
        for project in resQuery["out"]:
            if project == projectName:
                result["comment"] = "Project exists"
                result["status"] = True
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " Репозиторий с именем " + projectName + " в группе с  id: " + groupId + " существует")
                return result
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Репозиторий с именем " + projectName + " в группе с  id: " + groupId + " не существует")
    return result


def _createSubGroup(prefixUrl, groupId, groupName, token):
    """
    Создает подгруппу и
    Возвращает True в поле status если подгруппа создана
    и информацию о новой подгруппе в поле out
    """
    global printLog
    result = {
        "name": groupName,
        "changes": {},
        "status": False,
        "comment": "Новая подгруппа не создана",
        "out": {}
    }
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Запускаем процедуру создания подгруппы с именем " + groupName + " в группе с  id: " + groupId + " не существует")
    if printLog == "all" or printLog == "trace":
        print("Param's set to: ")
        print("     prefixUrl: " + prefixUrl)
        print("     groupId: " + groupId)
        print("     groupName: " + groupName)
    subgroup_path = groupName.lower()
    if not resQuery["status"]:
        d = dict(
            path=subgroup_path,
            name=groupName,
            parent_id=groupId,
            visibility="private"
        )
        data = urllib.parse.urlencode(d).encode("utf-8")
        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
        url = prefixUrl + "/groups/"
        resQuery = _sendUrlRequest(
            url,
            sslCheck=False,
            data=data,
            method='POST',
            headers=headers
        )
        if resQuery["status"]:
            result["status"] = True
            result["comment"] = "Group " + groupName + " was created"
            result["out"] = resQuery["out"]
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Группа с именем " + groupName + " в группе с  id: " + groupId + " создана")
        else:
            result["status"] = False
            result["comment"] = resQuery["comment"]
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Группа с именем " + groupName + " в группе с  id: " + groupId + " не  создана")
    else:
        result["status"] = True
        result["comment"] = "Group " + groupName + " already exists"
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def cmdRun(command, cwd="/", shell=True, nocwd=False):
    """
    Выполняет указанную команду в shell
    """
    global printLog
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Выполнение команды shell: " + command)
    result = {
        "name": command,
        "changes": {},
        "status": False,
        "comment": "Command finished unsuccessfuly",
        "out": {}
    }
    if printLog == "all" or printLog == "trace":
        print("Param's set to: ")
        print("     command: " + command)
        print("     cwd: " + cwd)
    if nocwd:
        sp = subprocess.run(
            shlex.split(command),
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
    else:
        sp = subprocess.run(
            shlex.split(command),
            shell=shell,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
    result["out"] = dict(
            stdout=sp.stdout,
            stderr=sp.stderr,
            returncode=sp.returncode
        )
    if sp.returncode == 0:
        result["status"] = True
        result["comment"] = "Command finished successfuly"
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _gitClone(cloneDir, url, token, project_path, bare=True):
    """
    Клонирует репозиторий в указанную папку
    """
    result = {
        "name": "",
        "changes": {},
        "status": False,
        "comment": "git clone false",
        "out": {}
    }
    global printLog
    if printLog == "all" or printLog == "trace":
        print("Repository clone params set to: ")
        print("     cloneDir: " + cloneDir)
        print("     url: " + url)
        print("     path: " + project_path)
    result = cmdRun("test -d " + cloneDir, cwd="/", shell=False)
    if result["status"]:
        result = cmdRun("rm -Rf " + cloneDir, shell=False)
    result = cmdRun("mkdir -p " + cloneDir, shell=False)
    if bare:
        cmd = "git clone --bare https://" \
            + url + ":" + token + '@' + url + "/" + project_path + " ."
    else:
        cmd = "git clone https://" \
            + url + ":" + token + '@' + url + "/" + project_path + " ."
    result = cmdRun(cmd, cwd=cloneDir, shell=False)
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _getGroupInfo(prefixUrl, groupId, subGroupName, token):
    """
    Возвращает полную информацию по подгруппе в поле out
    """
    url = prefixUrl + "groups/" + groupId + \
        "/subgroups?pagination=keyset&per_page=100&order_by=name&sort=asc"
    result = {
        "name": url,
        "changes": {},
        "status": False,
        "comment": "",
        "out": {}
    }
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    resQuery = _sendUrlRequest(
        url,
        sslCheck=False,
        data=None,
        method='GET',
        headers=headers
    )
    result["comment"] = resQuery["comment"]
    if resQuery["status"]:
        numberPages = resQuery["response"].getheader('X-Total-Pages')
        result["status"] = True
        if numberPages == "1":
            for subgroup in resQuery["out"]:
                if subgroup["name"] == subGroupName:
                    result["comment"] = "subGroup exists"
                    result["status"] = True
                    result["out"] = subgroup
        else:
            url = prefixUrl + "groups/" + groupId + \
                "/subgroups?pagination=keyset&per_page=100"
            resQuery = _sendUrlRequest(
                url,
                sslCheck=False,
                data=None,
                method='GET',
                headers=headers
            )
            for subgroup in resQuery["out"]:
                if subgroup["name"] == subGroupName:
                    result["comment"] = "subGroup exists"
                    result["status"] = True
                    result["out"] = subgroup
    return result


def _getProjectInfo(prefixUrl, groupId, projectName, token):
    """
    Возвращает полную информацию по проекту в поле out
    """
    global printLog
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Запрос полной информации по репозиторию с именем " + projectName + " в группе с id: " + groupId)
    if printLog == "all" or printLog == "trace":
        print("Repository info params set to: ")
        print("     prefixUrl2: " + prefixUrl)
        print("     parent2Id: " + groupId)
        print("     projectName: " + projectName)
    url = prefixUrl + "groups/" + groupId + \
        "/projects?pagination=keyset&per_page=100&order_by=name&sort=asc"
    result = {
        "name": url,
        "changes": {},
        "status": False,
        "comment": "",
        "out": []
    }
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    resQuery = _sendUrlRequest(
        url,
        sslCheck=False,
        data=None,
        method='GET',
        headers=headers
    )
    result["comment"] = resQuery["comment"]
    if resQuery["status"]:
        numberPages = resQuery["response"].getheader('X-Total-Pages')
        result["status"] = True
        if numberPages == "1":
            for project in resQuery["out"]:
                if project["name"] == projectName:
                    result["comment"] = "Project exists"
                    result["status"] = True
                    result["out"] = project
        else:
            url = prefixUrl + "groups/" + groupId + \
                "/projects?pagination=keyset&per_page=100"
            resQuery = _sendUrlRequest(
                url,
                sslCheck=False,
                data=None,
                method='GET',
                headers=headers
            )
            for project in resQuery["out"]:
                if project["name"] == projectName:
                    result["comment"] = "Project exists"
                    result["status"] = True
                    result["out"] = project
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _createProject(prefixUrl, groupId, projectName, token):
    """
    Создает проект и
    Возвращает True в поле status если проект создан
    и информацию о новом проекте в поле out
    """
    result = {
        "name": projectName,
        "changes": {},
        "status": False,
        "comment": "Project doesn't created",
        "out": {}
    }
    global printLog
    if printLog == "all" or printLog == "trace":
        print("Repository create params set to: ")
        print("     prefixUrl: " + prefixUrl)
        print("     groupId: " + groupId)
        print("     projectName: " + projectName)
    resQuery = _projectExists(prefixUrl, groupId, projectName, token)
    if not resQuery["status"]:
        d = dict(
            path=projectName,
            name=projectName,
            namespace_id=groupId,
            visibility="private"
        )
        data = urllib.parse.urlencode(d).encode("utf-8")
        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
        url = prefixUrl + "projects"
        resQuery = _sendUrlRequest(
            url,
            sslCheck=False,
            data=data,
            method='POST',
            headers=headers
        )
        if resQuery["status"]:
            result["status"] = True
            result["comment"] = "Project " + projectName + " was created"
            result["out"] = resQuery["out"]
        else:
            result["status"] = False
            result["comment"] = resQuery["comment"]
    else:
        result["status"] = True
        result["comment"] = "Project " + projectName + " already exists"
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _deleteProject(prefixUrl, projectId, token):
    """
    Создает подгруппу и
    Возвращает True в поле status если проект создан
    """
    result = {
        "name": projectId,
        "changes": {},
        "status": True,
        "comment": "Project already absent",
        "out": {}
    }
    global printLog
    if printLog == "all" or printLog == "trace":
        print("Repository delete params set to: ")
        print("     prefixUrl: " + prefixUrl)
        print("     projectId: " + projectId)
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    url = prefixUrl + "projects/" + projectId
    resQuery = _sendUrlRequest(
        url,
        sslCheck=False,
        data=None,
        method='DELETE',
        headers=headers
    )
    if resQuery["status"]:
        result["status"] = True
        result["comment"] = "Project " + projectId + " was deleted"
        result["out"] = resQuery["out"]
    else:
        result["status"] = False
        result["comment"] = resQuery["comment"]
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _gitPushRepo(cloneDir, url, token, path_with_namespace, mirror=True, options=''):
    """
    Pushed репозиторий из указанной папки
    """
    result = {
        "name": "",
        "changes": {},
        "status": False,
        "comment": "git push false",
        "out": {}
    }
    global printLog
    if printLog == "all" or printLog == "trace":
        print("Repository push  params set to: ")
        print("     cloneDir: " + cloneDir)
        print("     Url: " + url)
        print("     path_with_namespace: " + path_with_namespace)
    if mirror:
        cmd = "git push --mirror " + options + " https://" + url + ":" + \
            token + '@' + url + "/" + path_with_namespace + ".git"
    else:
        cmd = "git push " + options + " https://" + url + ":" + \
            token + '@' + url + "/" + path_with_namespace + ".git"
    result = cmdRun(cmd, cwd=cloneDir, shell=False)
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _gitMirrorLevel(
    cloneDir,
    url1,
    token1,
    parent1Id,
    url2,
    token2,
    parent2Id
):
    """
    Клонирует проекты и группы на уровене(без вложенных)
    """
    result = {
        "name": parent1Id,
        "changes": {},
        "status": False,
        "comment": "git mirror level false",
        "out": {}
    }
    global printLog
    global params
    prefixUrl1 = "https://" + url1 + "/api/v4/"
    prefixUrl2 = "https://" + url2 + "/api/v4/"
    FirstLevelSubGroups = _getFirstLevelSubGroups(
        prefixUrl1,
        parent1Id,
        token1
    )
    if not FirstLevelSubGroups == []:
        for groupName in FirstLevelSubGroups["out"]:
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Processing group '" + groupName + "'")
            result = _subGroupExists(prefixUrl2, parent2Id, groupName, token2)
            if not result["status"]:
                result = _createSubGroup(
                    prefixUrl2, parent2Id, groupName, token2
                )
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " subGroup '" + groupName + "' created")
            else:
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " subGroup '" + groupName + "' already exists")
        resultGroup = {
            "changes": FirstLevelSubGroups["out"],
            "comment": "git mirror level subGroups success",
        }

    else:
        resultGroup = {
            "changes": [],
            "comment": "git group doesn't have subGroups",
        }
    GroupProjects = _getGroupProjects(prefixUrl1, parent1Id, token1)
    if not GroupProjects == []:
        for projectName in GroupProjects["out"]:
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Processing repository '" + projectName + "'")
            result = _getProjectInfo(
                prefixUrl1, parent1Id, projectName, token1
            )
            project_path = result["out"]["namespace"]["full_path"] + \
                "/" + projectName + ".git"
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " git clone repository '" + projectName +
                      "' from source")
            result = _gitClone(
                cloneDir=cloneDir, url=url1,
                token=token1, project_path=project_path
            )
            if result["status"]:
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " Checking the existence of the repository" +
                          " in target")
                result = _getProjectInfo(
                    prefixUrl2, parent2Id, projectName, token2
                )
                if result["status"] and not result["out"] == []:
                    projectId = str(result["out"]["id"])
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " Repository exists with ID: " + projectId)
                    result = _deleteProject(prefixUrl2, projectId, token2)
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " Delete repository with ID: " + projectId)
                else:
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " Repository doesn't exists")
                time.sleep(300)
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " New Repository will be created")
                result = _createProject(
                    prefixUrl2,  parent2Id, projectName, token2
                )
                if printLog == "all" or printLog == "debug" or printLog == "trace":
                    dt = time.ctime()
                    print(dt + " New Repository created")
                time.sleep(10)
                if result["status"]:
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " New Repository get project info")
                    result = _getProjectInfo(
                        prefixUrl2, parent2Id, projectName, token2
                    )
                if result["status"]:
                    projectId = str(result["out"]["id"])
                    path_with_namespace = \
                        result["out"]["namespace"]["full_path"] + \
                        "/" + projectName
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " Mirroring new repository with full path: "
                              + path_with_namespace)
                    result = _gitPushRepo(
                        cloneDir,
                        url2,
                        token2,
                        path_with_namespace
                    )
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " New repository mirorred")
                if result["status"]:
                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                        dt = time.ctime()
                        print(dt + " Delete temporary path and files ")
                    result = cmdRun("rm -Rf " + cloneDir, shell=False)
                if result["status"]:
                    for source in params["addFiles"]:
                        name = source["name"]
                        find = False
                        for target in source["targets"]:
                            branch = target["branch"]
                            if target["targetRepo"] in project_path:
                                find = True
                                if "targetPath" in target:
                                    targetPath = target["targetPath"]
                                else:
                                    targetPath = ""
                                if printLog == "all" or printLog == "debug" or printLog == "trace":
                                    dt = time.ctime()
                                    print(dt + " git clone repository '" + projectName +
                                          "' from source for add new files")
                                result = _gitClone(
                                    cloneDir=cloneDir,
                                    url=url2,
                                    token=token2,
                                    project_path=path_with_namespace + ".git",
                                    bare = False
                                )
                                if result["status"]:
                                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                                        dt = time.ctime()
                                        print(dt + " git clone '" + projectName +
                                              "' success trying to add a new files")
                                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                                        dt = time.ctime()
                                        print(dt + " Переключаемся на ветку " + branch)
                                    result = cmdRun("git checkout " + branch, cwd=cloneDir, shell=False)
                                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                                        dt = time.ctime()
                                        print(dt + " Копируем файл " + name)
                                    result = cmdRun("cp -f " + " " + name + " " + cloneDir + targetPath, shell=False, nocwd=True)
                                    if printLog == "all" or printLog == "debug" or printLog == "trace":
                                        dt = time.ctime()
                                        print(dt + " File " + name + " was added in branch: " + branch)
                        if find:
                            if printLog == "all" or printLog == "debug" or printLog == "trace":
                                dt = time.ctime()
                                print(dt + " Фиксируем изменения в репозитории " + projectName)
                            result = cmdRun("git config --global user.email '" + params["git"]["user"]["email"] + "'", shell=False)
                            result = cmdRun("git config --global user.name '" + params["git"]["user"]["name"] + "'", shell=False)
                            result = cmdRun("git add --all . ", cwd=cloneDir, shell=False)
                            result = cmdRun("git commit -m 'Add new files after repository cloning'", cwd=cloneDir, shell=False)
                            result = _gitPushRepo(
                                cloneDir,
                                url2,
                                token2,
                                path_with_namespace,
                                mirror=False,
                                options='-o ci.skip'
                            )
                        else:
                            if printLog == "all":
                                dt = time.ctime()
                                print(dt + " Compare target with full path repository: ")
                                print("        "  + "target: " + target["targetRepo"])
                                print("        "  + "project path: " + project_path)
                            if printLog == "all" or printLog == "trace":
                                print(dt + " Compare target with full path repository unsuccessful!!! ")
                    headers = {
                        'Authorization': 'Bearer ' + token2,
                        'Content-Type': 'application/json'
                            }
                    for source in params["addApiRequests"]:
                        request = source["request"]
                        method = source["method"]
                        preffix = source["preffix"]
                        data = source["data"].encode("utf-8")
                        for target in source["targets"]:
                            if target["targetRepo"] in project_path:
                                url = prefixUrl2 + preffix + projectId + request
                                resQuery = _sendUrlRequest(
                                    url,
                                    sslCheck=False,
                                    data=data,
                                    method=method,
                                    headers=headers
                                )
                                if ( printLog == "all" or printLog == "debug" or printLog == "trace") and result["status"]:
                                    dt = time.ctime()
                                    print(dt + " Webhook was added in repo: " + target["targetRepo"])
                result = {
                    "name": parent1Id,
                    "changes": {"Projects": GroupProjects["out"],
                                "subGroups": resultGroup["changes"]},
                    "status": True,
                    "comment": "git mirror groups level success, " +
                    resultGroup["comment"],
                    "out": {}
                }
    else:
        result = {
            "changes": {"Projects": [], "subGroups": resultGroup["changes"]},
            "status": True,
            "comment": "git group doesn't have projects, " +
            resultGroup["comment"]
        }
    if printLog == "all" or printLog == "trace":
        print(result)
    return result


def _gitCloneTree(
    cloneDir,
    url1,
    token1,
    parent1Id,
    url2,
    token2,
    parent2Id
):
    '''
    Выполняет рекурсивное клонирование по уровням,
    до последнего вложенног уровня
    '''
    result = {
        "name": parent1Id,
        "changes": {},
        "status": False,
        "comment": "git mirror tree false",
        "out": {}
    }
    global printLog
    prefixUrl1 = "https://" + url1 + "/api/v4/"
    prefixUrl2 = "https://" + url2 + "/api/v4/"
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Start mirroring level")
    _gitMirrorLevel(
        cloneDir=cloneDir,
        url1=url1,
        token1=token1,
        parent1Id=parent1Id,
        url2=url2,
        token2=token2,
        parent2Id=parent2Id
    )
    if printLog == "all" or printLog == "debug" or printLog == "trace":
        dt = time.ctime()
        print(dt + " Level mirroring completed")
    subGroups = _getFirstLevelSubGroups(
                prefixUrl1, parent1Id, token1
            )["out"]
    result = {"changes": {"subGroups": subGroups}}
    if not result["changes"]["subGroups"] == []:
        for subGroup in result["changes"]["subGroups"]:
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Source and Target subGroupName: " + subGroup)
            subGroupId = str(
                _getGroupInfo(
                    prefixUrl1,
                    parent1Id,
                    subGroup,
                    token1
                )["out"]["id"]
            )
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Source subGroupId: " + subGroupId)
            sgTarget = _getGroupInfo(
                    prefixUrl2,
                    parent2Id,
                    subGroup,
                    token2
            )
            sgTargetId = str(sgTarget["out"]["id"])
            if printLog == "all" or printLog == "debug" or printLog == "trace":
                dt = time.ctime()
                print(dt + " Target subGroupId: " + sgTargetId)
            _gitCloneTree(
                cloneDir=cloneDir,
                url1=url1,
                token1=token1,
                parent1Id=subGroupId,
                url2=url2,
                token2=token2,
                parent2Id=sgTargetId
            )
    return "Finished"


def main():

    """
    variable indicies:
    1 - source
    2 - target
    Parameters description
    1) Source url - url1
    2) Source access token - token1
    3) Target url - url2
    4) Target access token - token2
    5) Target root Group ID - root2Id
    6) Source root Group ID - root1Id
    7) Temporary directory fo  git clone - cloneDir
    8) Log level - printLog
    printLog = "trace" полный вывод: список действий,
        входные параметры, результат выполнения функции
    printLog = "debug" краткий вывод: список действий
    printLog = "all" наиболее полный вывод: debug + результаты сравнений
    9) File with additional params - configFile
    """
    global printLog
    global params
    url1 = sys.argv[1]
    token1 = sys.argv[2]
    url2 = sys.argv[3]
    token2 = sys.argv[4]
    root2Id = sys.argv[5]
    root1Id = sys.argv[6]
    cloneDir = sys.argv[7]
    printLog = sys.argv[8]
    configFile = sys.argv[9]
    if printLog == "all" or printLog == "trace":
        print("Param's set to: ")
        print("     SourceUrl: " + url1)
        print("     TsrgetUrl: " + url2)
        print("     SourceRootGroupID: " + root1Id)
        print("     TargetRootGroupID: " + root2Id)
        print("     Dir for git clone: " + cloneDir)
        print("     Log level: " + printLog)
        print("     Params file: " + configFile)
    with open(configFile, 'r') as f:
        params = yaml.safe_load(f)
    _gitCloneTree(
        cloneDir,
        url1,
        token1,
        root1Id,
        url2,
        token2,
        root2Id
    )


if __name__ == "__main__":
    main()

