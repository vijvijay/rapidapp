<?php

include "vghead.php";
include "lastloginlog.php";

//$latest_ami_id = 'ami-8c8687de';

#output
# -1 	wait. try again after a few seconds automatically (this happens during session migrate
# -99	Cluster overloaded. Tell user "some problem with cloud. pls try later"

//get and parse arguments
$uid = $_REQUEST['uid'];
$ip  = $_SERVER['REMOTE_ADDR'];
login2db($uid, $ip);

$conn = getDBConnection(); 

//Check session state
$state = "nosession";
$dbpublicip = "";
$query = "select * from sessions where userid = '$uid'";
$result = mysql_query($query, $conn);
if($row = mysql_fetch_array($result)){
	$termination_mark 	= $row['termination_mark'];
	$dbpublicip		= $row['publicip'];
	if($termination_mark == 0){
		$state = "session_active";
	}else{
		$state = "session_migrate";
	}
}else{
	$state = "nosession";
}

//Give IP based on session state
if($state == "nosession"){
	//$query = "select * from farmstatus where ami_id='$latest_ami_id' and load_pct < 90 order by load_pct limit 1";
	$query = "select * from farmstatus where donot_allocate=false and load_pct < 60 order by load_pct limit 1";
	$result = mysql_query($query, $conn);
	if($row = mysql_fetch_array($result)){ //least loaded node
		$instanceid	= $row['instanceid'];
		$cores 		= $row['cores_ht'];
		$publicip	= $row['publicip'];
		//Assuming 10%-core as the load required per user,...
		//Even if we are wrong, the next update from the node will set the actuals into DB
		$load_pct_increase = 10 / $cores;
		$query = "update farmstatus set load_pct = load_pct + $load_pct_increase, free_core_pct = free_core_pct - 10 where instanceid = '$instanceid'";
		mysql_query($query, $conn);
		echo $publicip;
	}else{
		//All nodes in cluster are loaded above 90%. Do NOT admit more nodes till situation improves!!!
		echo "-99";
	}
}else if($state == "session_active"){
	//session is active. May be the session got disrupted due to network problem
	echo $dbpublicip;
}else if($state == "session_migrate"){
	//session migration in process. Ask the client sw to try after a few seconds automatically
	echo "-1";
}else{
	//unknown state
	echo "-1000";
}

closeDBConnection($conn);

?>
