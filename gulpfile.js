//Required
var gulp = require('gulp'),
    config = require('./app/config.json'),
    mustache = require("gulp-mustache-plus"),
    url = require('url'),
    proxy = require('proxy-middleware'),
    browserSync = require('browser-sync'),
    reload = browserSync.reload,
    del = require('del'),
    uglify = require('gulp-uglify'),
    rename = require('gulp-rename'),
    sass = require('gulp-sass'),
    plumber = require('gulp-plumber'),
    sourcemaps = require('gulp-sourcemaps'),
    htmlInclude = require('gulp-html-tag-include'),
    autoprefixer = require('gulp-autoprefixer');
//Scripts Task
gulp.task('scripts', function (){
  gulp.src(['app/js/**/*.js','!app/js/**/*.min.js'])
  .pipe(plumber())
  .pipe(rename({suffix:'.min'}))
  .pipe(sourcemaps.init())
  .pipe(uglify())
  .pipe(sourcemaps.write('../maps'))
  .pipe(gulp.dest('app/js'))
  .pipe(reload({stream:true}));
});

//Sass Task

gulp.task('styles', function(){
  gulp.src('app/scss/**/*.scss')
  .pipe(plumber())
  .pipe(sass().on('error', sass.logError))
  .pipe(autoprefixer('last 2 versions'))
  .pipe(gulp.dest('app/css'))
  .pipe(reload({stream:true}));
});

//HTML Task

gulp.task('mustache', function(){
  gulp.src('app/templates/**/*.mustache')
  .pipe(plumber())
  .pipe(mustache(config))
  .pipe(gulp.dest('app/'))
  .pipe(reload({stream:true}));
});

//Browser-Sync Task

gulp.task('browser-sync', function(){
  var proxyOptions = url.parse('http://localhost:5555/api');
  proxyOptions.route = '/api';

  browserSync({
    server:{
      baseDir: "./app/",
      index: "login.html",
      middleware: [proxy(proxyOptions)]
    }
  });
});

//Test the build before it goes out
gulp.task('build:serve', function(){
  browserSync({
    server:{
      baseDir: "./login/",
      index: "login.html"
    }
  });
});
//watch tasks
gulp.task('watch',function (){
  gulp.watch('app/js/**/*.js',['scripts']);
  gulp.watch('app/scss/**/*.scss',['styles']);
  gulp.watch('app/templates/**/*.mustache',['mustache']);
});

//Build Tasks

gulp.task('build:clean', function(cb){
  del([
    'login/**'
  ], cb);
});

gulp.task('build:copy', function(){
  return gulp.src('app/**/*')
  .pipe(gulp.dest('login'));
});

gulp.task('build:tidy', ['build:copy'], function(cb){
  del([
    'login/scss/',
    'login/templates/',
    'login/js/!(*.min.js)',
    'login/bower_components/**/src/',
    'login/bower_components/**/dist/!(*.min.js)',
    'login/bower_components/**/js/!(*.min.js)'
  ], cb);
});

gulp.task('build',['build:clean','scripts','styles','mustache','build:copy','build:tidy']);
//Default Task
gulp.task('default', ['scripts','styles','mustache','browser-sync','watch']);
