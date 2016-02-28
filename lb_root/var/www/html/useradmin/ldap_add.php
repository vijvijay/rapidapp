<?php
error_reporting(E_ALL);

include("../lb/vghead.php");

$uid = "S01496";
$mail = 'x@schits.com';
$mobile = '9876543210';
$name = $uid;
$pass = $uid . '@123';
$uidNumber = getNextUidNumber();

adduser($uid, $mail, $mobile, $name, $pass, $uidNumber);

function getNextUidNumber(){
	$conn = getDBConnection();
	mysql_query("lock tables nextuid write");
	$result = mysql_query("select * from nextuid");
	$row = mysql_fetch_array($result);
	$uidNum = $row['nextuid'];
	mysql_query("update nextuid set nextuid = nextuid + 1");
	mysql_query("unlock tables");
	closeDBConnection($conn);
	return $uidNum;
}

function salt($str){
	return $str; //for now no salting passwords
//	return '^' . $str . '._$';
}

function userdirname($uname){
	return "/nfshome/apprimenfs/" . substr(md5(salt($uname)), -3) . "/" . $uname . "/";
}

function create_userdir_onNFSserver($uname){
	$diskquota = 1024;
	$dirname = "/apprimenfs/" . substr(md5(salt($uname)), -3) . "/" . $uname . "/";
	system("sudo mkdir -p $dirname");
	system("sudo chown -R $uname.cloudusers $dirname");
	system("sudo chmod 700 $dirname");
	system("sudo quotatool -u $uname -bq ${diskquota}M -l '$diskquota Mb' /apprimenfs");
}

function adduser($uid, $mail, $mobile, $name, $pass, $uidNumber){
	$AD_server = "ldap://localhost";
	$dn = "cn=$uid,ou=users,dc=appocloud,dc=com";
	$ds = ldap_connect($AD_server);
	if ($ds) {
		ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3); // IMPORTANT
		$result = ldap_bind($ds, "cn=admin,dc=appocloud,dc=com", "superStar@3947"); //BIND
		$ldaprecord['objectclass'][0] = "inetOrgPerson";
		$ldaprecord['objectclass'][1] = "posixAccount";
		$ldaprecord['objectclass'][2] = "top";
		$ldaprecord['cn'] = $uid;
		$ldaprecord['givenName'] = $uid;
		$ldaprecord['sn'] = $uid;
		$ldaprecord['uid'] = $uid;
		$ldaprecord['uidNumber'] = $uidNumber;
		$ldaprecord['gidNumber'] = '100000';//clouduser group
		$ldaprecord['userPassword'] = '{MD5}' . base64_encode(pack('H*',md5(salt($pass))));
		$ldaprecord['loginShell'] = '/bin/vgsh';
		$ldaprecord['homeDirectory'] = userdirname($uid, "ap-southeast-1");

		$r = ldap_add($ds, $dn, $ldaprecord);

		//create the home directory
		create_userdir_onNFSserver($uid);
		
	} else {
		echo "cannot connect to LDAP server at $AD_server.";
	}
}
?>
