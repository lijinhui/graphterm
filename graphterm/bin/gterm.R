# gterm.R: Convenience functions to display inline graphics within GraphTerm

# Plotting example:
#   g <- gcairo()          # Initialize Cairo device for GraphTerm output
#   x <- rnorm(100,0,1)
#   hist(x, col="blue")
#   g$frame()              # Display plot as inline image
#   hist(x, col="red")
#   g$frame(TRUE)          # Overwrite previous plot
#
# Initialize notebook mode, using R-markdown file:
#   gnotebook("R-example1.R.md")
#

gcairo <- function(width=400, height=300, test=FALSE) {
  # Initialized window using Cairo graphics device with specified width/height
  # Returns list object with function gframe to display plot.
  #   gframe(overwrite=FALSE)
  grequired()
  gcat <- FALSE
  goverwrite <- FALSE
  cdev <- Cairo(width, height, type='raster')

  Cairo.onSave(cdev, function(dev, page) {
    if (!gcat)
      return()
    gsave(writePNG(Cairo.capture(cdev)), goverwrite, test=test)
    gcat <<- FALSE
    goverwrite <<- FALSE
  })

  list(frame = function(overwrite=FALSE) {
    gcat <<- TRUE
    goverwrite <<- overwrite
    frame()
  })
}

gnotebook <- function(filepath="") {
  gwrite(paste('{"x_gterm_response": "open_notebook",',
               '"x_gterm_parameters": {"filepath": "', filepath, '",',
               '"prompts": [], "current_directory": "', Sys.getenv("PWD"),'"} }\n\n', sep=""))
}

gwrite <- function(data) {
  # Displays text data wrapped with GraphTerm prefix and suffix
  prefix <- paste("\x1b[?1155;", Sys.getenv("GTERM_COOKIE"), "h", sep="")
  suffix <- "\x1b[?1155;l"
  cat(prefix, data, suffix, sep="")
}

grequired <- function() {
  install = ''
  if (!require("RCurl", quietly=TRUE))
    install = paste(install, "RCurl")
  if (!require("Cairo", quietly=TRUE))
    install = paste(install, "Cairo")
  if (!require("png", quietly=TRUE))
    install = paste(install, "png")

  if (nchar(install)) 
    stop(paste("Please install the following R packages to display inline graphics:", install))
}

gsave <- function(pngdata, overwrite=FALSE, test=False) {
  # Displays PNG image data within a GtaphTerm pagelet
  prefix <- paste("\x1b[?1155;", Sys.getenv("GTERM_COOKIE"), "h", sep="")
  suffix <- "\x1b[?1155;l"

  image64 <- base64(pngdata)

  # Create image blob
  blobid = paste(sample(1:1000000,1), sample(1:1000000,1), sep="")
  imagepfx <- paste('<!--gterm data blob=', blobid, '-->image/png;base64,', sep='')
  gwrite(paste(imagepfx, image64, sep=""))

  if (overwrite) {
    overs = ' overwrite=yes'
  } else {
    overs = ''
  }

  # Display blob
  pagelet <- paste('<!--gterm pagelet display=block blob=', blobid, overs, '--><div class="gterm-blockhtml"><img class="gterm-blockimg" src="/_blob/local/', blobid, '"></div>', sep='')
  if (test) {
    cat(pagelet, " page=", page, sep="")
  } else {
    gwrite(pagelet)
  }
}
  
gshow <- function(overwrite=FALSE) {
  gsave(writePNG(dev.capture(native=TRUE)), overwrite)
}

gpng <- function(width=400, height=300, test=FALSE) {
  # Alternative approach to displaying plot
  png(filename="gterm_tem.png", width=width, height=height)
  setHook("plot.new", function() {
    ## Does not work until second plot
    ## gsave(readBin("gterm_tem.png",what="raw",n=2e6), test=test)
  })
}
