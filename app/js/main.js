$(function() {
  addListeners();
});

function addListeners() {
  $("#login").click(function(){
    login();
  });
}

function login(){
  var username = $("input[name='username']").val();
  var password = $("input[name='password']").val();
  var passwordHashed = md5(password);
  var currentURL = document.location;
  $(".login-message").html("Logging in");
  $.post("api/login",
    {
      username:username,
      password:passwordHashed
    })
  .done(function(data, status){
    //move the browser location to the new url
    if(currentURL.hash!==undefined){
      document.location.assign(currentURL.origin+currentURL.hash);
    }
  })
  .fail(function(data){
    if(data.status === 403){
      $(".login-message").html("Username or password invalid.");
    }
  });
}
