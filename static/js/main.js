$(document).ready(function(){
	var pid = $("#pid").val();
    //Edit Button
	$("#editbutton").click(function(){
        curruser = $("#curruser").val();
		username = $("#username").val();

		if (curruser == username)
		{
			$("#modal1").modal();
		}
		else
		{
			$("#errorModal").modal();
		}

});
    //Edit Post
	$("#postedit").click(function(){
		var title = $("#subject").val();
		var description = $("#content").val();
		var pid = $("#pid").val();
		$.post("/postedit", {
			subject: title,
			content: description,
			pid: pid
		}, function(data) {
			var x = $.parseJSON(data);
			if (x.error)
			{
				alert("ERROR");
			}
			else
			{
				alert(x.message);
				location.replace("/thread/"+pid)
			}

		});

	});

    //Delete Post
	$("#postdelete").click(function(){
		var pid = $("#pid").val();
		username = $("#username").val();
		curruser = $("#curruser").val();

		if (curruser == username)
		{
			$.post("/delete", {
				pid: pid
			}, function(data) {
				var x = $.parseJSON(data);
				if (x.error)
				{
					alert("ERROR");
				}
				else
				{
					alert(x.message);
					location.replace("/home")
				}
			});
		}

	});
    //Delete Button
	$("#deleteeditbutton").click(function(){
		username = $("#username").val();
		curruser = $("#curruser").val();
		if (username == curruser)
		{
			$("#deletePost").modal();
		}
	});

    //Comment Button
	$("#commentbutton").click(function(){
		username = $("#username").val();

		var pid = $("#pid").val();
		var username = $("#username").val();
		var c = $("#comment").val();
		$.post("/comment", {
				pid: pid,
				username: username,
				comment: c
			}, function(data) {
				var x = $.parseJSON(data);
				if (x.error)
				{
					alert("ERROR");
				}
				else
				{
					location.replace("/thread/"+pid);
				}
		});

	});
	//Edit Comment
	$("#editcomm").click(function(){
		var pid = $("#pid").val();
		var c = $("#descriptioncomment").val();
		var usercomment = $("#editcomment").val();
		$.post("/editcomment", {
					usercomment: usercomment,
					comment: c
				}, function(data) {
					var x = $.parseJSON(data);
					if (x.error)
					{
						alert("ERROR");
					}
					else
					{
						alert(x.message);
						location.replace("/thread/"+pid)
					}
			});
	});
    //Edit Comment Button
	$(".editcombutton").click(function(){
		var divin = $(this).parent().closest('.panel').attr('id');
		$.post("/usercomment", {
					usercomment: divin,
				}, function(data) {
					var x = $.parseJSON(data);
					if (x.error)
					{
						alert("ERROR");
					}
					else
					{
						$("#descriptioncomment").val(x.comment);
						$("#editcomment").val(divin);
						$("#modalcomment").modal();
					}
			});
	});
    //Delete Comment Button
	$(".deletecommbutton").click(function(){
		var divin = $(this).parent().closest('.panel').attr('id');
		$("#deletecommentModal").modal();
		$("#deletecomment").click(function(){
			$.post("/deletecomment", {
					usercomment: divin,
				}, function(data) {
					var x = $.parseJSON(data);
					if (x.error)
					{
						alert("ERROR");
					}
					else
					{
						$("#deletecommentModal").modal('hide');
						$("#"+divin).remove();
						//window.location.reload();
					}
			});
		})
	});
});