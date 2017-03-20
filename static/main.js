$(document).ready(function(){

  $(".list-group-item").on("click", function(){
    $(".delete-item").removeClass("active");
    $(this).find("span").addClass("active");
  });



});
