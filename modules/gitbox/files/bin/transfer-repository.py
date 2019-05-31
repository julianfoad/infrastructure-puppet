#!/usr/bin/python -B

import sys
import argparse
import requests
import json

url="https://api.github.com"

def getOpts ():
        parser = argparse.ArgumentParser(description='github api caller')
        parser.add_argument('-d', '--dest', required=False, default="apache", help="New repository owner, defaults to 'apache'")
        parser.add_argument('-v', '--victim', required=True, help="New repository owner")
        parser.add_argument('-o', '--origin', required=False, default="ApacheInfra", help="original repo owner, defaults to 'ApacheInfra'")
        parser.add_argument('-n', '--newname', help="name of repository under new owner")
        parser.add_argument('-t', '--tokenfile', required=True, help='token file')
        parser.add_argument('-s', '--slug', help='team with access to new repo')
        args = parser.parse_args()
        return args

# Check github org for group slug
def slugInOrg (org, slug, head):
    """ Returns github group id when provided a github group slug
        Requires org to search, github group slug, and the headers (with token embedded)"""

    group = requests.get(url + "/orgs/" + org + "/teams/" + slug, headers=head).json()
    return group

# Check github org for repostory
def repoInOrg (org, victim, head):
    """ Returns github group id when provided a github group slug
        Requires org to search, github group slug, and the headers (with token embedded)"""
    repo = requests.get(url + "/repos/" + org + "/" + victim, headers=head).json()
    return repo

# Rename a repository in a given github org
def renameRepo (victim, newname, org, head):
    """ Rename the repository
        requires reponame, newname, org, headers (with token embedded)"""
    rename_data={ "name": newname }
    uri=url + "/repos/" + org + "/" + victim
    r=requests.patch(uri, headers=head, data=json.dumps(rename_data)).json()

# Transfer a repository to a new github org
def transferRepo (victim, dest, origin, group_id, head):
    """ Transfer the repository <victim> from <origin> to <dest> with ID as the team with perms for the repo.
        requires: victim repository, destination org, origin org, groupID in destination, and headers with token embedded"""
        
    head['Accept']='application/vnd.github.nightshade-preview+json'
    transfer_data = {
        'new_owner': dest,
        'team_ids': [
            group_id
        ]
    }
    r = requests.post(url + "/repos/" + origin +"/" + victim + "/transfer", headers=head, data=json.dumps(transfer_data)).json()

# Update the permissions for a given group to a repository. 
def updatePerms (victim, group_id, perms, org, head):
    """ Update Permissions to the repositories
        requires: victim repository, group id, permission level as string (pull, push, admin), organization, and headers (with token embedded)"""
    head['Accept']="application/vnd.github.inertia-preview+json"
    perms_data = { 'permission': perms } 
    new_url = url + "/teams/" + str(group_id.get('id')) + "/repos/" + org + "/" + victim.get('name')
    try:
        r = requests.put(new_url, headers=head, data=json.dumps(perms_data)).json()
    except ValueError:
        sys.exit(0)

def main():
    # Fetch Args
    args = getOpts()
    token_file = open(args.tokenfile,"r")
    my_token = token_file.readlines()[0].rstrip()
    head={ 'Authorization': 'token ' + my_token }

    # Only continue if the $org/$repo combination is valid.
    # Return $?=2 if the repository doesn't exist
    has_repo = repoInOrg(args.origin, args.victim, head)
    if has_repo.get('message'):
        print "Requested repo: " + args.victim + " does not exist in the specified origin"
        sys.exit(2)

    # (OPTIONAL) If no newname is provided use the original name.
    if not args.newname:
        newname=args.victim
    else:
        newname=args.newname

    # Check to see if the requested new name is already present in the destination org
    # return $?=2 if a repository with that name already exists.
    repo_in_dest = repoInOrg(args.dest, newname, head)
    if not repo_in_dest.get('message'):
        print "Requested repository: " + newname + " already exists in the destination org"
        sys.exit(2)

    sys.exit(100)
    # Only continue if the specified group exists in the destination org.
    # Return $?=3 if the group doesn't exist
    has_group = slugInOrg(args.dest, args.slug, head)
    if not has_group.get('id'):
        print "No group named: " + args.slug + " exists in the specified destination org"
        sys.exit(3)

    # Transfer the repository
    transferRepo(args.victim, args.dest, args.origin, has_group.get('id'), head)

    # Rename the repository (whether the name has changed or not)
    # This could be eliminated if args.newname isn't provided but w/e
    renameRepo(args.victim, newname, args.origin, head)

    # Update the permissions of the group that has been assigned to the repository in the destination org to write
#    updatePerms(has_repo, has_group, "push", args.dest, head)

if __name__ == "__main__":
        main()

