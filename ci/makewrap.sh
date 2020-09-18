#!/usr/bin/env bash

dotenv=$(which dotenv 2> /dev/null)

if [ $? -ne 0 ]
then
  /bin/bash "$@"
  exit $?
fi

if [[ -f $HOME/.env ]]
then
  cmd="dotenv -f ${HOME}/.env run "
fi

if [[ -f .env ]]
then
  cmd="${cmd}dotenv -f .env run "
fi

if [[ -f tmp/.env ]]
then
  cmd="${cmd}dotenv -f tmp/.env run "
fi

${cmd} /bin/bash "$@"
exit $?