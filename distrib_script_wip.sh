PROJECT_DIRPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
docker run \
    --rm \
    --workdir='/usr/src/myapp' \
    -v "${PROJECT_DIRPATH}:/usr/src/myapp" \
    python:3.8 bash -c "pip install -r requirements.txt;
                               pip3 install pyinstaller;
                               pyinstaller script_wip.py --onefile\
                               --clean -y\
                               --distpath=dist/linux/ ;
                               chown -R ${UID} dist; "