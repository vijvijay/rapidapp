<?php

include "vghead.php";

//get and parse arguments
$procs 		= $_REQUEST['procs'];
$cpuidle 	= $_REQUEST['cpuidle'];
$instanceid 	= $_REQUEST['instanceid'];
$localip	= $_REQUEST['localip'];
$publicip	= $_REQUEST['publicip'];
$instance_type	= $_REQUEST['instance_type'];
$ami_id		= $_REQUEST['ami_id'];
$az		= $_REQUEST['az'];
$up_secs	= $_REQUEST['up_secs'];
$up_idle_secs	= $_REQUEST['up_idle_secs'];
$no_of_sessions	= $_REQUEST['no_of_sessions'];

//compute other values
$load_pct = 100 - $cpuidle;
$free_core_pct = $cpuidle * $procs;
$jusmins = ((int)($up_secs/60) + 2 ) % 60; // 2 mins = safety time for bootup - 1 should be sufficient
$mins_to_renewal = 60 - $jusmins; 
$up_idle_secs = (int) $up_idle_secs / $procs ;

$conn = getDBConnection(); 

$query = "select * from farmstatus where instanceid = '$instanceid'";
$result = mysql_query($query, $conn);
if($row = mysql_fetch_array($result)){ //row already present.
	$query = "update farmstatus set localip='$localip', publicip='$publicip', cores_ht=$procs, load_pct=$load_pct, 
		free_core_pct=$free_core_pct, no_of_sessions=$no_of_sessions, instance_type='$instance_type', 
		ami_id='$ami_id', az='$az', mins_to_renewal=$mins_to_renewal, up_secs=$up_secs, 
		up_idle_secs=$up_idle_secs, last_update_time=NOW() where instanceid='$instanceid'"; 
}else{
	$query = "insert into farmstatus 
		(instanceid, localip, publicip, cores_ht, load_pct, free_core_pct, no_of_sessions, instance_type, 
		ami_id, az, mins_to_renewal, up_secs, up_idle_secs, creation_time, last_update_time) values 
		('$instanceid', '$localip', '$publicip', $procs, $load_pct, $free_core_pct, $no_of_sessions, '$instance_type',
		'$ami_id', '$az', $mins_to_renewal, $up_secs, $up_idle_secs, NOW(), NOW())";
}
mysql_query($query, $conn);
closeDBConnection($conn);

echo 1;

?>
