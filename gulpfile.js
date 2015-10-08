//Required
var gulp = require('gulp'),
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

gulp.task('html', function(){
  gulp.src('app/html/pages/**/*.html')
  .pipe(plumber())
  .pipe(htmlInclude())
  //TODO: use gulp-if for to handle index.html http://stackoverflow.com/questions/27181719/gulp-condition-inside-pipe
  .pipe(gulp.dest('app/pages'))
  .pipe(reload({stream:true}));
});

//Browser-Sync Task

gulp.task('browser-sync', function(){
  browserSync({
    server:{
      baseDir: "./app/"
    }
  });
});

//Test the build before it goes out
gulp.task('build:serve', function(){
  browserSync({
    server:{
      baseDir: "./build/"
    }
  });
});
//watch tasks
gulp.task('watch',function (){
  gulp.watch('app/js/**/*.js',['scripts']);
  gulp.watch('app/scss/**/*.scss',['styles']);
  gulp.watch('app/**/*.html',['html']);
});

//Build Task

gulp.task('build:clean', function(cb){
  del([
    'build/**'
  ], cb);
});

gulp.task('build:copy', function(){
  return gulp.src('app/**/*')
  .pipe(gulp.dest('build'));
});

gulp.task('build:tidy', ['build:copy'], function(cb){
  del([
    'build/scss/',
    'build/js/!(*.min.js)'
  ], cb);
});

gulp.task('build',['build:copy','build:tidy']);
//Default Task
gulp.task('default', ['scripts','styles','html','browser-sync','watch']);
