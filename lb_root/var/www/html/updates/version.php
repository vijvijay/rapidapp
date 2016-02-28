<?php
#latest version
$server_str_version = "0.6.7";

if(!isset($_REQUEST['version']) || $_REQUEST['prgname'] != 'RapidApp'){
	echo "0";
	exit;
}

$clistrversion 	= $_REQUEST['version'];
$cliversion 	= version_str2int($clistrversion);
$latestversion	= version_str2int($server_str_version);

if($latestversion > $cliversion){
	echo $clistrversion;
}else{
	echo "0";
}


//functions from here on
function version_str2int($strversion){
	$version = 0;
	$versionarray = explode(".", $strversion);
	for($i=0; $i<sizeof($versionarray); $i++){
		$version = $version * 100 + intval($versionarray[$i]);
	}
	return $version;
}

?>
