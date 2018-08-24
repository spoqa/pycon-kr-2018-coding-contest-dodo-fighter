# 도도 파이터

![Dodo Fighter](https://spoqa.github.io/images/2018-08-08/dodofighter.png)

## 요구사항

- [Python] 3.6+
- [PostgreSQL]

## 설치 방법

### 요구사항 설치하기

1. [Python] 3.6 이상을 설치합니다.
1. [PostgreSQL]을 설치합니다.
   * OS X 사용자는 [Postgres.app](http://postgresapp.com/)을 통해서 설치하실 수 있습니다.

### GitHub OAuth 앱 생성

1. GitHub에서 [새 어플리케이션을 등록](https://github.com/settings/applications/new)합니다.
1. Authorization Callback URL은 정해진 서버 주소 뒤에 `/oauth/authorized`가 붙은 형태로 입력해 주십시오.
   * 만약 `http://localhost:5021`에서 서버를 돌리고자 한다면 `http://localhost:5021/oauth/authorized`가 됩니다.
1. 등록 완료 후 Client ID와 Client Secret를 기억해 주십시오.

### 서버 설정

1. PostgreSQL 데이터베이스를 생성합니다.

        $ createdb dodo-fighter
        
1. 설정 파일을 복사합니다.

        $ cp sample.toml local.toml
        
1. 설정 파일(`local.html`)을 고칩니다.

    * `database.url` 항목에 위에서 설정한 PostgreSQL DB를 입력해 주십시오.
        
            예: postgresql://localhost:5432/dodo-fighter
        
    * `[github]` 섹션 아래에는 위에서 설정한 GitHub OAuth App의 Client ID와 Client Secret를 입력해 주십시오.
    
    * `web.secret_key`는 랜덤한 16바이트의 문자열을 입력해 주십시오.
    
1. 가상 환경을 설정합니다. 여기서는 bash 기준으로 설명합니다.

    1. `venv` 모듈을 이용하여 가상 환경을 만듭니다.

            $ python -m venv env
            
    1. 가상 환경으로 진입합니다.
    
            $ . env/bin/activate
            
    1. 의존 패키지들을 설치합니다.
    
            $ pip install -r requirements.txt
            
    1. 스크립트를 설치합니다.
    
            $ python setup.py install
            
## 실행 방법

1. 실행 전에는 가상 환경에 진입한 상태여야 합니다.

        $ . env/bin/activate
        
1. 서버를 실행합니다.

        $ python run.py -d local.toml

  [Python]: http://www.python.org
  [PostgreSQL]: http://www.postgresql.org
